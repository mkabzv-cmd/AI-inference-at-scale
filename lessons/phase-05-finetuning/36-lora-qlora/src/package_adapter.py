#!/usr/bin/env python3
"""Create an immutable hash manifest for a PEFT adapter directory."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--base-model-id", required=True)
    parser.add_argument("--base-revision", required=True)
    parser.add_argument("--dataset-manifest-sha256", required=True)
    parser.add_argument("--training-config-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for value in (
        args.dataset_manifest_sha256,
        args.training_config_sha256,
    ):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("input hashes must be 64 lowercase hexadecimal")
    if not (40 <= len(args.base_revision) <= 64) or any(
        c not in "0123456789abcdef" for c in args.base_revision
    ):
        raise SystemExit("base revision must be a 40-64 character hexadecimal commit")
    files = []
    for path in sorted(args.adapter_dir.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"adapter package must not contain symlinks: {path}")
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(args.adapter_dir)),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
    required = {row["path"] for row in files}
    if "adapter_config.json" not in required:
        raise SystemExit("adapter_config.json is required")
    if not any(name.endswith(".safetensors") for name in required):
        raise SystemExit("a safetensors adapter weight file is required")
    adapter_config = json.loads(
        (args.adapter_dir / "adapter_config.json").read_text()
    )
    if adapter_config.get("base_model_name_or_path") != args.base_model_id:
        raise SystemExit("adapter config base model ID differs from package input")
    adapter_revision = adapter_config.get(
        "revision", adapter_config.get("base_model_revision")
    )
    if adapter_revision != args.base_revision:
        raise SystemExit(
            "adapter config revision differs from package input"
        )
    manifest = {
        "schema_version": 1,
        "artifact_type": "peft-adapter",
        "base_model_id": args.base_model_id,
        "base_model_revision": args.base_revision,
        "dataset_manifest_sha256": args.dataset_manifest_sha256,
        "training_config_sha256": args.training_config_sha256,
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"PASS: packaged {len(files)} adapter files")


if __name__ == "__main__":
    main()
