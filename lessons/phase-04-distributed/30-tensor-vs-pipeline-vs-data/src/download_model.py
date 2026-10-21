#!/usr/bin/env python3
"""Download one exact model revision into a node-local cache."""

from __future__ import annotations

import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download


model_id = os.environ["MODEL_ID"]
revision = os.environ["MODEL_REVISION"]
path = Path("/models/snapshot")
resolved = Path(
    snapshot_download(
        repo_id=model_id,
        revision=revision,
        local_dir=path,
        token=os.environ.get("HF_TOKEN") or None,
    )
)
total = sum(
    item.stat().st_size
    for item in resolved.rglob("*")
    if item.is_file() and not item.is_symlink()
)
marker = {
    "model_id": model_id,
    "revision": revision,
    "total_bytes": total,
}
(path.parent / ".model-provenance.json").write_text(
    json.dumps(marker, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({"event": "model_staged", **marker}, sort_keys=True))
