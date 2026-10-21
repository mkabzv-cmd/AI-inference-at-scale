#!/usr/bin/env python3
"""Verify staging/production pointers and promotion history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--expected-release", required=True)
    args = parser.parse_args()
    failures = []
    for environment in ("staging", "production"):
        path = args.state_dir / f"{environment}.json"
        if not path.is_file():
            failures.append(f"{environment} state missing")
            continue
        state = json.loads(path.read_text(encoding="utf-8"))
        if state["release_id"] != args.expected_release:
            failures.append(
                f"{environment} points to {state['release_id']}, "
                f"expected {args.expected_release}"
            )
        if state["environment"] != environment:
            failures.append(f"{environment} embedded environment differs")
    history_path = args.state_dir / "promotion-history.ndjson"
    history = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(history) < 2:
        failures.append("promotion history is incomplete")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        f"PASS: staging and production point to {args.expected_release}; "
        f"history contains {len(history)} transition(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
