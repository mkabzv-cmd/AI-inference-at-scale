#!/usr/bin/env python3
"""Package adapter metadata, cards, and hashes into one immutable release."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require_hash(name, value):
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SystemExit(f"{name} must be 64 lowercase hexadecimal characters")


def copy_tree_files(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"release inputs must not contain symlinks: {path}")
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--base-metadata-dir", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--data-card", type=Path, required=True)
    parser.add_argument("--model-card", type=Path, required=True)
    parser.add_argument("--dataset-manifest-sha256", required=True)
    parser.add_argument("--training-config-sha256", required=True)
    parser.add_argument("--evaluation-lock-sha256", required=True)
    parser.add_argument("--release-gates-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    for name, value in (
        ("dataset manifest hash", args.dataset_manifest_sha256),
        ("training config hash", args.training_config_sha256),
        ("evaluation lock hash", args.evaluation_lock_sha256),
        ("release gates hash", args.release_gates_sha256),
    ):
        require_hash(name, value)
    input_paths = (
        args.config,
        args.base_metadata_dir,
        args.adapter_dir,
        args.data_card,
        args.model_card,
    )
    output_resolved = args.output.resolve()
    for source in input_paths:
        if not source.exists():
            raise SystemExit(f"release input is absent: {source}")
        source_resolved = source.resolve()
        if (
            output_resolved == source_resolved
            or output_resolved in source_resolved.parents
            or source_resolved in output_resolved.parents
        ):
            raise SystemExit(
                "release output must not overlap any input path"
            )
    if args.output.is_symlink():
        raise SystemExit("release output must not be a symlink")
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    copy_tree_files(args.base_metadata_dir, args.output / "base-metadata")
    copy_tree_files(args.adapter_dir, args.output / "adapter")
    shutil.copy2(args.data_card, args.output / "DATA_CARD.md")
    shutil.copy2(args.model_card, args.output / "MODEL_CARD.md")
    config = json.loads(args.config.read_text())
    shutil.copy2(args.config, args.output / "release-config.json")

    adapter_names = {
        path.name for path in (args.output / "adapter").iterdir() if path.is_file()
    }
    if "adapter_config.json" not in adapter_names:
        raise SystemExit("adapter_config.json is required")
    if args.fixture:
        if "adapter_weights.fixture.json" not in adapter_names:
            raise SystemExit("fixture package requires adapter_weights.fixture.json")
    elif not any(name.endswith(".safetensors") for name in adapter_names):
        raise SystemExit("deployable adapter release requires safetensors weights")

    files = []
    for path in sorted(args.output.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(args.output)),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
    manifest = {
        "schema_version": 1,
        "artifact_type": "course-fixture" if args.fixture else "peft-adapter",
        "deployable": not args.fixture,
        "release_name": config["release_name"],
        "served_adapter_name": config["served_adapter_name"],
        "adaptation_method": config["adaptation_method"],
        "base_model": config["base_model"],
        "tokenizer": config["tokenizer"],
        "dataset_contract": config["dataset_contract"],
        "dataset_manifest_sha256": args.dataset_manifest_sha256,
        "training_config_sha256": args.training_config_sha256,
        "evaluation_contract": config["evaluation_contract"],
        "evaluation_lock_sha256": args.evaluation_lock_sha256,
        "release_gates_sha256": args.release_gates_sha256,
        "benchmark_contract": config["benchmark_contract"],
        "files": files,
    }
    (args.output / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"PASS: built {manifest['artifact_type']} release with "
        f"{len(files)} hashed files"
    )


if __name__ == "__main__":
    main()
