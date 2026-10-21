#!/usr/bin/env python3
"""Bind artifact/evidence hashes and create an exact evidence index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


MARKER = re.compile(r"__[A-Z][A-Z0-9_]+__")


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise ValueError(f"unsafe relative path: {value!r}")
    return path.as_posix()


def confined_path(workspace: Path, relative: str, must_exist: bool = True) -> Path:
    root = workspace.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlinked workspace path is forbidden: {relative}")
    if must_exist:
        resolved = candidate.resolve(strict=True)
    else:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        resolved = candidate.parent.resolve(strict=True) / candidate.name
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"workspace path escapes root: {relative}") from error
    return candidate


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--confirm",
        required=True,
        help="Must equal <project-id>:bind-evidence.",
    )
    parser.add_argument(
        "--replace-index",
        action="store_true",
        help="Explicitly replace an existing evidence-index.json.",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    contract_path = confined_path(workspace, "contract.json")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    project_id = str(contract["project_id"])
    if args.confirm != f"{project_id}:bind-evidence":
        raise SystemExit("typed confirmation does not match project and operation")
    if contract.get("validation_mode") != "operator-run":
        raise SystemExit("finalization is reserved for an operator-run workspace")
    release_rel = safe_relative(str(contract["paths"]["release"]))
    index_rel = safe_relative(str(contract["paths"]["evidence_index"]))
    release_path = confined_path(workspace, release_rel)
    index_path = confined_path(workspace, index_rel, must_exist=False)
    if index_path.exists() and not args.replace_index:
        raise SystemExit("evidence index exists; pass --replace-index to replace it")

    required = [safe_relative(str(item)) for item in contract["required_files"]]
    if len(required) != len(set(required)):
        raise SystemExit("contract required_files contains duplicates")
    if index_rel in required:
        raise SystemExit("evidence index cannot include itself in required_files")
    if release_rel not in required or "contract.json" not in required:
        raise SystemExit("required_files must include contract.json and release.json")
    if index_rel in {release_rel, "contract.json"}:
        raise SystemExit("evidence index path must be distinct from contract and release")
    resolved_required = {}
    failures = []
    for rel in required:
        try:
            path = confined_path(workspace, rel)
            if not path.is_file():
                raise ValueError("not a regular file")
            resolved_required[rel] = path
        except (FileNotFoundError, ValueError) as error:
            failures.append(f"{rel}: {error}")
    if failures:
        raise SystemExit(f"required files are unsafe or missing: {failures}")

    release = json.loads(release_path.read_text(encoding="utf-8"))
    serving = release["serving"]
    evaluation = release["evaluation"]
    adapter = release["adapter"]
    rag = release["rag"]
    referenced = {
        safe_relative(str(serving["configuration_path"])),
        safe_relative(str(evaluation["dataset_path"])),
        safe_relative(str(adapter["path"])),
        safe_relative(str(rag["path"])),
        *(
            safe_relative(str(gate["evidence_path"]))
            for gate in release.get("gates", [])
        ),
    }
    if not referenced.issubset(set(required)):
        raise SystemExit(
            "release references files outside required_files: "
            f"{sorted(referenced - set(required))}"
        )
    serving["configuration_sha256"] = file_hash(
        confined_path(
            workspace, safe_relative(str(serving["configuration_path"]))
        )
    )
    evaluation["dataset_sha256"] = file_hash(
        confined_path(workspace, safe_relative(str(evaluation["dataset_path"])))
    )
    adapter["sha256"] = file_hash(
        confined_path(workspace, safe_relative(str(adapter["path"])))
    )
    rag["sha256"] = file_hash(
        confined_path(workspace, safe_relative(str(rag["path"])))
    )

    for gate in release.get("gates", []):
        evidence_path = confined_path(
            workspace, safe_relative(str(gate["evidence_path"]))
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if gate.get("status") != "pass" or evidence.get("status") != "pass":
            raise SystemExit(f"gate is not explicitly pass: {gate.get('name')}")
        if evidence.get("origin") != "observed":
            raise SystemExit(f"gate is not observed evidence: {gate.get('name')}")
        gate["evidence_sha256"] = file_hash(evidence_path)

    rendered_release = json.dumps(release, indent=2, sort_keys=True) + "\n"
    files_for_scan: dict[str, bytes] = {}
    for rel in required:
        files_for_scan[rel] = (
            rendered_release.encode("utf-8")
            if rel == release_rel
            else resolved_required[rel].read_bytes()
        )
    unresolved = []
    for rel, raw in files_for_scan.items():
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if MARKER.search(text):
            unresolved.append(rel)
    if unresolved:
        raise SystemExit(f"unresolved markers remain: {unresolved}")

    atomic_json(release_path, release)
    entries = []
    for rel in sorted(required):
        suffix = Path(rel).suffix.lower()
        kind = {
            ".json": "json",
            ".md": "markdown",
            ".yaml": "kubernetes",
            ".yml": "kubernetes",
        }.get(suffix, "artifact")
        entries.append(
            {
                "path": rel,
                "sha256": file_hash(confined_path(workspace, rel)),
                "kind": kind,
            }
        )
    index = {
        "schema_version": 1,
        "project_id": project_id,
        "release_id": contract["release_id"],
        "generated_by": "lesson-49-finalize-workspace-v1",
        "entries": entries,
    }
    atomic_json(index_path, index)
    print(f"release={release_path}")
    print(f"evidence_index={index_path}")
    print(f"entries={len(entries)}")
    print("verification=not-yet-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
