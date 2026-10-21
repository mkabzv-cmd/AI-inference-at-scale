#!/usr/bin/env python3
"""Populate a model directory with one exact Hugging Face snapshot."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import huggingface_hub
from huggingface_hub import snapshot_download


MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
MODEL_REVISION = os.environ.get(
    "MODEL_REVISION",
    "7ae557604adf67be50417f59c2c2f167def9a775",
)
MODEL_PATH = Path(os.environ.get("MODEL_PATH", "/models/snapshot"))
READY_PATH = MODEL_PATH.parent / ".model-provenance.json"


def log(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def current_provenance() -> dict[str, object] | None:
    try:
        return json.loads(READY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def bytes_on_disk(path: Path) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and not item.is_symlink()
    )


def main() -> int:
    existing = current_provenance()
    current_bytes = bytes_on_disk(MODEL_PATH) if MODEL_PATH.is_dir() else 0
    if (
        MODEL_PATH.is_dir()
        and existing
        and existing.get("model_id") == MODEL_ID
        and existing.get("revision") == MODEL_REVISION
        and existing.get("total_bytes") == current_bytes
        and current_bytes > 0
    ):
        log(
            "model_cache_hit",
            model_id=MODEL_ID,
            revision=MODEL_REVISION,
            total_bytes=current_bytes,
        )
        return 0

    if existing:
        log(
            "model_cache_marker_rejected",
            marker_model_id=existing.get("model_id"),
            marker_revision=existing.get("revision"),
            marker_total_bytes=existing.get("total_bytes"),
            observed_total_bytes=current_bytes,
        )

    # Never leave an old completion marker beside a snapshot being replaced.
    # A failed download must remain visibly incomplete on the next init run.
    READY_PATH.unlink(missing_ok=True)

    if MODEL_PATH.exists():
        log("remove_stale_snapshot", path=str(MODEL_PATH))
        shutil.rmtree(MODEL_PATH)
    MODEL_PATH.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    log(
        "model_download_started",
        model_id=MODEL_ID,
        revision=MODEL_REVISION,
        path=str(MODEL_PATH),
    )
    try:
        snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_dir=MODEL_PATH,
            token=os.environ.get("HF_TOKEN") or None,
        )
    except Exception as exc:  # noqa: BLE001 - preserve useful Pod log evidence
        log(
            "model_download_failed",
            error=type(exc).__name__,
            message=str(exc),
        )
        return 1

    provenance = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "huggingface_hub_version": huggingface_hub.__version__,
        "total_bytes": bytes_on_disk(MODEL_PATH),
    }
    temporary = READY_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(READY_PATH)
    log(
        "model_download_finished",
        seconds=round(time.monotonic() - started, 3),
        **provenance,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
