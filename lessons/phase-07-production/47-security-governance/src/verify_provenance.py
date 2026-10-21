#!/usr/bin/env python3
"""Fail closed when bundle bytes, paths, or declared licenses differ."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_relative(value: str) -> str:
    relative = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != value
    ):
        raise ValueError(f"unsafe bundle path: {value!r}")
    return relative.as_posix()


def confined_file(bundle_dir: Path, relative: str) -> Path:
    root = bundle_dir.resolve()
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{relative}: symlinked path is forbidden")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    if not candidate.is_file():
        raise ValueError(f"{relative}: not a regular file")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    provenance = json.loads(args.provenance.read_text(encoding="utf-8"))
    failures = []
    expected = {}
    for declaration in config.get("files", []):
        try:
            relative = safe_relative(str(declaration["path"]))
        except (KeyError, ValueError) as error:
            failures.append(str(error))
            continue
        if relative in expected:
            failures.append(f"{relative}: duplicate config declaration")
        expected[relative] = declaration
    if provenance.get("bundle_name") != config.get("bundle_name"):
        failures.append("bundle_name differs from reviewed config")
    if provenance.get("bundle_version") != config.get("bundle_version"):
        failures.append("bundle_version differs from reviewed config")
    if not isinstance(provenance.get("artifacts"), list):
        failures.append("provenance artifacts must be an array")
        artifacts = []
    else:
        artifacts = provenance["artifacts"]
    declared = set()
    for artifact in artifacts:
        try:
            relative = safe_relative(str(artifact["path"]))
        except (KeyError, ValueError) as error:
            failures.append(str(error))
            continue
        if relative in declared:
            failures.append(f"{relative}: duplicate provenance declaration")
        declared.add(relative)
        reviewed = expected.get(relative)
        if reviewed is None:
            failures.append(f"{relative}: not declared by reviewed config")
        else:
            for field in ("role", "license", "source"):
                if artifact.get(field) != reviewed.get(field):
                    failures.append(f"{relative}: {field} differs from reviewed config")
        try:
            path = confined_file(args.bundle_dir, relative)
        except (FileNotFoundError, ValueError) as error:
            failures.append(f"{relative}: missing, escaped, or not a regular file ({error})")
            continue
        observed = sha256_file(path)
        if observed != artifact["sha256"]:
            failures.append(f"{relative}: sha256 mismatch")
        if path.stat().st_size != artifact["size_bytes"]:
            failures.append(f"{relative}: size mismatch")
        if PurePosixPath(relative).suffix in {".bin", ".pt", ".pth", ".pkl", ".pickle"}:
            failures.append(f"{relative}: executable/deserializing format rejected")
    actual = set()
    bundle_root = args.bundle_dir.resolve()
    provenance_path = args.provenance.resolve()
    for path in args.bundle_dir.rglob("*"):
        relative = path.relative_to(args.bundle_dir).as_posix()
        if path.is_symlink():
            failures.append(f"{relative}: symlinked bundle entry is forbidden")
        elif path.is_file() and path.resolve() != provenance_path:
            try:
                path.resolve(strict=True).relative_to(bundle_root)
            except (FileNotFoundError, ValueError):
                failures.append(f"{relative}: file escapes the bundle root")
            else:
                actual.add(relative)
    if declared != set(expected):
        failures.append(
            f"provenance/config file set differs: "
            f"undeclared={sorted(declared - set(expected))} "
            f"missing={sorted(set(expected) - declared)}"
        )
    if actual != declared:
        failures.append(
            f"bundle file set differs: undeclared={sorted(actual - declared)} "
            f"missing={sorted(declared - actual)}"
        )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        f"PASS: {len(declared)} declared bundle artifacts match exact hashes "
        "and reviewed metadata/file set"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
