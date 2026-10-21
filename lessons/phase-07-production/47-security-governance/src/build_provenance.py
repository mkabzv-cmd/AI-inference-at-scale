#!/usr/bin/env python3
"""Create a hash- and license-bound provenance statement for a local bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_bundle_file(bundle_dir: Path, value: str) -> tuple[str, Path]:
    relative = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != value
    ):
        raise SystemExit(f"unsafe bundle path: {value!r}")
    root = bundle_dir.resolve()
    candidate = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SystemExit(f"symlinked bundle path is forbidden: {value}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"required regular file is missing or escaped: {value}") from error
    if not candidate.is_file():
        raise SystemExit(f"required regular file is missing: {value}")
    return relative.as_posix(), candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    allowed_licenses = set(config["allowed_licenses"])
    allowed_suffixes = set(config["allowed_artifact_suffixes"])
    records = []
    seen = set()
    for declaration in config["files"]:
        relative, path = resolve_bundle_file(
            args.bundle_dir, str(declaration["path"])
        )
        if relative in seen:
            raise SystemExit(f"duplicate bundle declaration: {relative}")
        seen.add(relative)
        suffix = PurePosixPath(relative).suffix
        if suffix not in allowed_suffixes:
            raise SystemExit(f"disallowed artifact suffix: {suffix}")
        if declaration["license"] not in allowed_licenses:
            raise SystemExit(
                f"license is not allowlisted: {declaration['license']}"
            )
        records.append(
            {
                **declaration,
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    payload = {
        "schema_version": 1,
        "bundle_name": config["bundle_name"],
        "bundle_version": config["bundle_version"],
        "artifacts": records,
        "claims": {
            "hashes_bind_exact_bytes": True,
            "licenses_are_declared_not_legally_adjudicated": True,
            "no_executable_model_artifact_is_in_this_teaching_bundle": True
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"provenance={args.output} artifacts={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
