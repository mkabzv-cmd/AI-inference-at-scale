#!/usr/bin/env python3
"""Render the private Kubernetes teaching template from a workspace contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath


TOKEN = re.compile(r"__[A-Z][A-Z0-9_]+__")
PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
NAMESPACE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")
RELEASE_ID = re.compile(r"^[A-Za-z0-9](?:[-A-Za-z0-9._]{1,61}[A-Za-z0-9])$")
MODEL_ID = re.compile(r"^[A-Za-z0-9](?:[-A-Za-z0-9._/]{1,198}[A-Za-z0-9])$")


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise SystemExit(f"unsafe workspace path: {value!r}")
    return path.as_posix()


def confined_output(workspace: Path, relative: str) -> Path:
    root = workspace.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise SystemExit(f"output parent may not be a symlink: {relative}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    try:
        candidate.parent.resolve(strict=True).relative_to(root)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"output path escapes workspace: {relative}") from error
    if candidate.is_symlink():
        raise SystemExit(f"output may not replace a symlink: {relative}")
    return candidate


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--confirm",
        help="Required with --replace; must equal <project-id>:render-private-manifest.",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    inputs = [workspace / name for name in ("contract.json", "release.json", "environment.json")]
    if any(path.is_symlink() for path in inputs):
        raise SystemExit("contract, release, and environment must be regular workspace files")
    contract = json.loads(inputs[0].read_text(encoding="utf-8"))
    release = json.loads(inputs[1].read_text(encoding="utf-8"))
    environment = json.loads(inputs[2].read_text(encoding="utf-8"))
    project_id = str(contract["project_id"])
    if not PROJECT_ID.fullmatch(project_id):
        raise SystemExit("contract project_id is not valid")
    if contract.get("serving_topology") != "one-gpu":
        raise SystemExit(
            "the built-in renderer supports one-gpu only; compose and review "
            "an engine-specific three-node manifest"
        )
    output = confined_output(
        workspace,
        safe_relative(str(contract["paths"]["kubernetes_manifest"])),
    )
    if output.exists() and not args.replace:
        raise SystemExit(f"output exists; no change made: {output}")
    if args.replace and args.confirm != f"{project_id}:render-private-manifest":
        raise SystemExit("typed confirmation does not match project and operation")
    if environment.get("network_exposure") != "private":
        raise SystemExit("environment must declare private network exposure")
    if environment.get("service_type") != "ClusterIP":
        raise SystemExit("environment service_type must be ClusterIP")
    if environment.get("serving_topology") != "one-gpu":
        raise SystemExit("environment topology must match the one-gpu template")
    for document_name, document in (
        ("release", release),
        ("environment", environment),
    ):
        for key in ("project_id", "environment_id", "release_id"):
            if document.get(key) != contract.get(key):
                raise SystemExit(f"{document_name} {key} differs from contract")
    if release.get("model") != contract.get("model"):
        raise SystemExit("release model identity differs from contract")
    if release.get("serving", {}).get("topology") != "one-gpu":
        raise SystemExit("release serving topology must match the one-gpu template")
    namespace = str(environment["namespace"])
    if not NAMESPACE.fullmatch(namespace):
        raise SystemExit("environment namespace must be a Kubernetes DNS label")
    release_id = str(release["release_id"])
    if not RELEASE_ID.fullmatch(release_id):
        raise SystemExit("release_id is unsafe for a Kubernetes label value")
    model_id = str(release["model"]["id"])
    if not MODEL_ID.fullmatch(model_id):
        raise SystemExit("model id contains unsafe manifest characters")
    model_revision = str(release["model"]["revision"])
    if not re.fullmatch(r"[0-9a-f]{40}", model_revision):
        raise SystemExit("model revision must be 40 lowercase hex")
    image = str(release["image"])
    if not re.fullmatch(r"[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}", image):
        raise SystemExit("release image is not digest-pinned")

    template = (
        Path(__file__).resolve().parents[1] / "templates" / "k8s" / "platform.yaml"
    ).read_text(encoding="utf-8")
    replacements = {
        "__NAMESPACE__": namespace,
        "__RELEASE_ID__": release_id,
        "__IMAGE__": image,
        "__MODEL_ID__": model_id,
        "__MODEL_REVISION__": model_revision,
    }
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    markers = sorted(set(TOKEN.findall(rendered)))
    if markers:
        raise SystemExit(f"unresolved manifest markers: {markers}")
    atomic_write(output, rendered)
    print(f"rendered={output}")
    print("exposure=private")
    print("apply=not-performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
