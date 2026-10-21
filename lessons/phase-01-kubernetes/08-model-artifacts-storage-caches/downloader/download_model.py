#!/usr/bin/env python3
"""Download one immutable model snapshot and record cache provenance."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import huggingface_hub
from huggingface_hub import snapshot_download


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
PROVENANCE_NAME = ".course-model-ready.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-id",
        default=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
    )
    parser.add_argument(
        "--revision",
        default=os.environ.get("MODEL_REVISION", DEFAULT_REVISION),
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(os.environ.get("MODEL_TARGET", "/models/snapshot")),
    )
    return parser.parse_args()


def emit(event: str, **fields: object) -> None:
    print(
        json.dumps({"event": event, **fields}, sort_keys=True),
        flush=True,
    )


def read_provenance(path: Path) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def byte_count(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def main() -> int:
    args = parse_args()
    target = args.target.resolve()
    provenance_path = target.parent / PROVENANCE_NAME
    existing = read_provenance(provenance_path)
    current_bytes = byte_count(target) if target.is_dir() else 0

    if (
        target.is_dir()
        and existing
        and existing.get("model_id") == args.model_id
        and existing.get("revision") == args.revision
        and existing.get("total_bytes") == current_bytes
        and current_bytes > 0
    ):
        emit(
            "model_ready",
            cache_hit=True,
            model_id=args.model_id,
            revision=args.revision,
            seconds=0.0,
            total_bytes=current_bytes,
        )
        return 0

    if existing:
        emit(
            "cache_marker_rejected",
            marker_model_id=existing.get("model_id"),
            marker_revision=existing.get("revision"),
            marker_total_bytes=existing.get("total_bytes"),
            observed_total_bytes=current_bytes,
        )

    # Remove the completion marker before changing the snapshot. If download
    # fails, a later run must not mistake a partial directory for a cache hit.
    provenance_path.unlink(missing_ok=True)

    if target.exists():
        emit("removing_stale_target", path=str(target))
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    emit(
        "download_started",
        model_id=args.model_id,
        revision=args.revision,
        target=str(target),
    )

    try:
        snapshot_download(
            repo_id=args.model_id,
            revision=args.revision,
            local_dir=target,
            token=os.environ.get("HF_TOKEN") or None,
        )
    except Exception as exc:  # noqa: BLE001 - emit a useful init-container log
        emit("download_failed", error=type(exc).__name__, message=str(exc))
        return 1

    elapsed = round(time.monotonic() - started, 3)
    provenance = {
        "model_id": args.model_id,
        "revision": args.revision,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "downloader": f"huggingface-hub/{huggingface_hub.__version__}",
        "total_bytes": byte_count(target),
    }

    temporary = provenance_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(provenance_path)

    emit(
        "model_ready",
        cache_hit=False,
        model_id=args.model_id,
        revision=args.revision,
        seconds=elapsed,
        total_bytes=provenance["total_bytes"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
