#!/usr/bin/env python3
"""Strictly verify release hashes, adapter/base binding, and tokenizer identity."""

import argparse
import hashlib
import json
import struct
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_safetensors(path):
    with path.open("rb") as handle:
        raw_length = handle.read(8)
        if len(raw_length) != 8:
            raise SystemExit(f"invalid safetensors header: {path.name}")
        header_length = struct.unpack("<Q", raw_length)[0]
        if header_length < 2 or header_length > 100 * 1024 * 1024:
            raise SystemExit(f"invalid safetensors header length: {path.name}")
        raw_header = handle.read(header_length)
        try:
            header = json.loads(raw_header)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SystemExit(f"invalid safetensors JSON header: {path.name}")
        data_bytes = path.stat().st_size - 8 - header_length
    tensors = [
        value for key, value in header.items() if key != "__metadata__"
    ]
    if not tensors:
        raise SystemExit(f"safetensors file contains no tensors: {path.name}")
    for tensor in tensors:
        if not {"dtype", "shape", "data_offsets"} <= set(tensor):
            raise SystemExit(f"incomplete safetensors tensor metadata: {path.name}")
        start, end = tensor["data_offsets"]
        if not (0 <= start <= end <= data_bytes):
            raise SystemExit(f"invalid safetensors data offsets: {path.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--allow-fixture", action="store_true")
    args = parser.parse_args()
    root = args.release
    manifest = json.loads((root / "release-manifest.json").read_text())
    if manifest.get("schema_version") != 1:
        raise SystemExit("unsupported release manifest schema version")
    if not isinstance(manifest.get("deployable"), bool):
        raise SystemExit("release deployable flag must be boolean")
    required = {
        "DATA_CARD.md",
        "MODEL_CARD.md",
        "release-config.json",
        "base-metadata/config.json",
        "base-metadata/snapshot.json",
        "base-metadata/tokenizer_config.json",
        "adapter/adapter_config.json",
        "adapter/training-provenance.json",
    }
    declared_paths = [row["path"] for row in manifest["files"]]
    if len(declared_paths) != len(set(declared_paths)):
        raise SystemExit("release manifest contains duplicate file paths")
    for value in declared_paths:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or value != path.as_posix():
            raise SystemExit(f"invalid release manifest path: {value}")
    declared = set(declared_paths)
    actual = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.name != "release-manifest.json"
    }
    symlinks = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_symlink()
    ]
    if symlinks:
        raise SystemExit(
            "release must not contain symlinks: " + ", ".join(symlinks)
        )
    if actual != declared:
        raise SystemExit(
            "declared and actual release file sets differ: "
            f"undeclared={sorted(actual - declared)}, "
            f"absent={sorted(declared - actual)}"
        )
    missing = sorted(required - declared)
    if missing:
        raise SystemExit("release is missing required files: " + ", ".join(missing))
    if not manifest["deployable"] and not args.allow_fixture:
        raise SystemExit("course fixture is not a deployable release")
    if manifest["deployable"]:
        if manifest["artifact_type"] != "peft-adapter":
            raise SystemExit("deployable adapter must use peft-adapter type")
        if not any(
            path.startswith("adapter/") and path.endswith(".safetensors")
            for path in declared
        ):
            raise SystemExit("deployable adapter has no safetensors weights")
        for path in sorted(declared):
            if path.startswith("adapter/") and path.endswith(".safetensors"):
                validate_safetensors(root / path)
    elif manifest["artifact_type"] != "course-fixture":
        raise SystemExit("nondeployable release must use course-fixture type")
    for row in manifest["files"]:
        path = root / row["path"]
        if not path.is_file():
            raise SystemExit(f"declared file is absent: {row['path']}")
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise SystemExit(f"artifact hash mismatch: {row['path']}")
    adapter = json.loads((root / "adapter/adapter_config.json").read_text())
    release_config = json.loads((root / "release-config.json").read_text())
    training_provenance = json.loads(
        (root / "adapter/training-provenance.json").read_text()
    )
    base_metadata = json.loads((root / "base-metadata/config.json").read_text())
    tokenizer_metadata = json.loads(
        (root / "base-metadata/tokenizer_config.json").read_text()
    )
    snapshot_metadata = json.loads(
        (root / "base-metadata/snapshot.json").read_text()
    )
    base = manifest["base_model"]
    tokenizer = manifest["tokenizer"]
    for field in (
        "release_name",
        "served_adapter_name",
        "adaptation_method",
        "base_model",
        "tokenizer",
        "dataset_contract",
        "evaluation_contract",
        "benchmark_contract",
    ):
        if release_config.get(field) != manifest.get(field):
            raise SystemExit(
                f"release config differs from manifest: {field}"
            )
    if manifest["deployable"] and any(
        value.get("course_fixture") is True
        for value in (
            adapter,
            training_provenance,
            base_metadata,
            tokenizer_metadata,
            snapshot_metadata,
        )
    ):
        raise SystemExit("deployable release contains course fixture metadata")
    for field in (
        "dataset_manifest_sha256",
        "training_config_sha256",
        "evaluation_lock_sha256",
        "release_gates_sha256",
    ):
        value = manifest[field]
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit(f"invalid provenance hash: {field}")
    revision = base["revision"]
    if not (40 <= len(revision) <= 64) or any(
        c not in "0123456789abcdef" for c in revision
    ):
        raise SystemExit("invalid immutable base revision")
    if adapter["base_model_name_or_path"] != base["id"]:
        raise SystemExit("adapter base model ID does not match release base")
    adapter_revision = adapter.get(
        "revision", adapter.get("base_model_revision")
    )
    if adapter_revision != base["revision"]:
        raise SystemExit("adapter base revision does not match release base")
    if training_provenance.get("base_model_id") != base["id"]:
        raise SystemExit("training provenance base model ID differs from release")
    if training_provenance.get("method") != manifest["adaptation_method"]:
        raise SystemExit(
            "training provenance adaptation method differs from release"
        )
    if training_provenance.get("base_model_revision") != base["revision"]:
        raise SystemExit(
            "training provenance base revision differs from release"
        )
    if training_provenance.get("dataset_manifest_sha256") != manifest[
        "dataset_manifest_sha256"
    ]:
        raise SystemExit(
            "training provenance dataset hash differs from release"
        )
    if training_provenance.get("training_config_sha256") != manifest[
        "training_config_sha256"
    ]:
        raise SystemExit(
            "training provenance config hash differs from release"
        )
    if int(training_provenance.get("rank", -1)) != int(adapter.get("r", -2)):
        raise SystemExit("training provenance rank differs from adapter config")
    if int(training_provenance.get("alpha", -1)) != int(
        adapter.get("lora_alpha", -2)
    ):
        raise SystemExit("training provenance alpha differs from adapter config")
    if sorted(training_provenance.get("targets", [])) != sorted(
        adapter.get("target_modules", [])
    ):
        raise SystemExit(
            "training provenance targets differ from adapter config"
        )
    if tokenizer["id"] != base["id"] or tokenizer["revision"] != base["revision"]:
        raise SystemExit("tokenizer identity differs from the trained base snapshot")
    if snapshot_metadata.get("model_id") != base["id"]:
        raise SystemExit("snapshot metadata model ID differs from release base")
    if snapshot_metadata.get("model_revision") != base["revision"]:
        raise SystemExit(
            "snapshot metadata model revision differs from release base"
        )
    if snapshot_metadata.get("tokenizer_id") != tokenizer["id"]:
        raise SystemExit(
            "snapshot metadata tokenizer ID differs from release tokenizer"
        )
    if snapshot_metadata.get("tokenizer_revision") != tokenizer["revision"]:
        raise SystemExit(
            "snapshot metadata tokenizer revision differs from release tokenizer"
        )
    if (
        base_metadata.get("_name_or_path") is not None
        and base_metadata["_name_or_path"] != base["id"]
    ):
        raise SystemExit("base metadata name differs from release base")
    if (
        tokenizer_metadata.get("name_or_path") is not None
        and tokenizer_metadata["name_or_path"] != tokenizer["id"]
    ):
        raise SystemExit("tokenizer metadata name differs from release tokenizer")
    if not manifest.get("served_adapter_name"):
        raise SystemExit("served adapter name is required")
    if manifest["benchmark_contract"] != "oms-benchmark/v1":
        raise SystemExit("unexpected benchmark contract")
    print(
        f"PASS: verified {len(manifest['files'])} hashes and exact "
        "base/tokenizer/adapter binding"
    )


if __name__ == "__main__":
    main()
