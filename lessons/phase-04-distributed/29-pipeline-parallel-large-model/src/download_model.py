#!/usr/bin/env python3
"""Stage exactly one model revision and write a provenance marker."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import huggingface_hub
from huggingface_hub import snapshot_download


model_id = os.environ["MODEL_ID"]
revision = os.environ["MODEL_REVISION"]
model_path = Path(os.environ.get("MODEL_PATH", "/models/snapshot"))
model_root = Path("/models").resolve()
resolved_model_path = model_path.resolve()
if (
    resolved_model_path == model_root
    or model_root not in resolved_model_path.parents
):
    raise SystemExit("MODEL_PATH must be a child of /models")
model_path = resolved_model_path
marker = model_path.parent / ".model-provenance.json"

if model_path.exists():
    shutil.rmtree(model_path)
model_path.mkdir(parents=True)
resolved = snapshot_download(
    repo_id=model_id,
    revision=revision,
    local_dir=model_path,
    token=os.environ.get("HF_TOKEN") or None,
)
resolved_path = Path(resolved)
total_bytes = sum(
    path.stat().st_size
    for path in resolved_path.rglob("*")
    if path.is_file() and not path.is_symlink()
)
record = {
    "model_id": model_id,
    "requested_revision": revision,
    "snapshot_path": str(resolved_path),
    "total_bytes": total_bytes,
    "huggingface_hub_version": huggingface_hub.__version__,
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
}
temporary = marker.with_suffix(".tmp")
temporary.write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
temporary.replace(marker)
print(json.dumps({"event": "model_staged", **record}, sort_keys=True))
