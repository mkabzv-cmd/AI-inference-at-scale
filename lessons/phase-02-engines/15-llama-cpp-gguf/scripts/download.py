#!/usr/bin/env python3
"""Download one declared GGUF and verify exact size plus SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "config" / "artifacts.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="qwen2.5-0.5b-instruct-q4_k_m.gguf")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "models")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    declared = {item["name"]: item for item in manifest["files"]}
    if args.name not in declared:
        raise SystemExit(f"undeclared artifact {args.name!r}; choose {sorted(declared)}")
    item = declared[args.name]
    url = (
        "https://huggingface.co/"
        f"{manifest['repository']}/resolve/{manifest['revision']}/{args.name}"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / args.name
    if destination.exists():
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if destination.stat().st_size == item["size_bytes"] and digest == item["sha256"]:
            print(f"verified existing {destination}")
            return 0
        raise SystemExit(f"existing file failed verification: {destination}")
    request = urllib.request.Request(url, headers={"User-Agent": "open-model-systems-course/1"})
    hasher = hashlib.sha256()
    size = 0
    fd, temporary_name = tempfile.mkstemp(prefix=args.name + ".", dir=args.output_dir)
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(
            request, timeout=60
        ) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                hasher.update(chunk)
                size += len(chunk)
        if size != item["size_bytes"]:
            raise RuntimeError(f"size mismatch: expected {item['size_bytes']}, got {size}")
        if hasher.hexdigest() != item["sha256"]:
            raise RuntimeError("SHA-256 mismatch")
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    print(f"downloaded and verified {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
