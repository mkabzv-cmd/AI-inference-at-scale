#!/usr/bin/env python3
"""Atomically move a local environment pointer with compare-and-swap."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from validate_release import validate_release


def read_release(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--environment", choices=("staging", "production"), required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument(
        "--expected-current",
        required=True,
        help="Expected release ID, or NONE when no state should exist.",
    )
    args = parser.parse_args()
    candidate = read_release(args.candidate)
    failures = validate_release(candidate)
    if failures:
        raise SystemExit(
            "candidate failed release validation: " + "; ".join(failures)
        )
    args.state_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.state_dir / f"{args.environment}.json"
    lock_path = args.state_dir / ".promotion.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = read_release(state_path) if state_path.exists() else None
        current_id = str(current["release_id"]) if current else "NONE"
        if current_id != args.expected_current:
            raise SystemExit(
                f"compare-and-swap failed: expected {args.expected_current}, "
                f"observed {current_id}"
            )
        state = {
            **candidate,
            "environment": args.environment,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "previous_release_id": None if current is None else current["release_id"],
        }
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{args.environment}.",
            suffix=".json",
            dir=args.state_dir,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, state_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

        history_path = args.state_dir / "promotion-history.ndjson"
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "environment": args.environment,
                        "from": current_id,
                        "to": candidate["release_id"],
                        "at": state["promoted_at"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    print(
        f"promoted environment={args.environment} "
        f"from={current_id} to={candidate['release_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
