#!/usr/bin/env python3
"""Validate cross-artifact compatibility and required release evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE = re.compile(r"^[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}$")
RELEASE_ID = re.compile(r"^[a-z0-9](?:[-a-z0-9.]{1,61}[a-z0-9])$")
VERSION = re.compile(r"^[A-Za-z0-9](?:[-A-Za-z0-9._]{0,61}[A-Za-z0-9])?$")
REQUIRED_GATES = {
    "quality-evaluation",
    "performance-slo",
    "security-policy",
}


def validate_release(release: object) -> list[str]:
    failures = []
    if not isinstance(release, dict):
        return ["release must be a JSON object"]

    if release.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if not RELEASE_ID.fullmatch(str(release.get("release_id", ""))):
        failures.append("release_id must be a Kubernetes-safe immutable identifier")
    if len(str(release.get("kind", "")).strip()) < 3:
        failures.append("kind must describe the release record")
    if not HEX40.fullmatch(str(release.get("source_revision", ""))):
        failures.append("source_revision must be an immutable 40-hex commit")
    if not IMAGE.fullmatch(str(release.get("image", ""))):
        failures.append("image must end in @sha256:<64 lowercase hex>")

    model = release.get("model", {})
    if not isinstance(model, dict):
        failures.append("model must be an object")
        model = {}
    if len(str(model.get("id", "")).strip()) < 3:
        failures.append("model id is required")
    revision = str(model.get("revision", ""))
    tokenizer_revision = str(model.get("tokenizer_revision", ""))
    if not HEX40.fullmatch(revision):
        failures.append("model revision must be 40 lowercase hex")
    if tokenizer_revision != revision:
        failures.append("tokenizer revision must match this release's model revision")

    adapter = release.get("adapter", {})
    if not isinstance(adapter, dict):
        failures.append("adapter must be an object")
        adapter = {}
    if not isinstance(adapter.get("enabled"), bool):
        failures.append("adapter enabled must be boolean")
    if adapter.get("enabled") is True:
        if adapter.get("format") != "safetensors":
            failures.append("enabled adapter format must be safetensors")
        if not HEX64.fullmatch(str(adapter.get("sha256", ""))):
            failures.append("adapter sha256 must be 64 lowercase hex")
        if adapter.get("base_model_revision") != revision:
            failures.append("adapter base revision differs from release model")

    index = release.get("index", {})
    if not isinstance(index, dict):
        failures.append("index must be an object")
        index = {}
    if not HEX64.fullmatch(str(index.get("sha256", ""))):
        failures.append("index sha256 must be 64 lowercase hex")
    index_version = str(index.get("version", ""))
    if (
        index_version.lower() in {"", "latest", "main"}
        or not VERSION.fullmatch(index_version)
    ):
        failures.append("index version must be immutable/versioned")
    if not HEX64.fullmatch(str(release.get("configuration_sha256", ""))):
        failures.append("configuration_sha256 must be 64 lowercase hex")

    gate_names = set()
    gates = release.get("gates", [])
    if not isinstance(gates, list):
        failures.append("gates must be an array")
        gates = []
    for gate in gates:
        if not isinstance(gate, dict):
            failures.append("each gate must be an object")
            continue
        name = str(gate.get("name", ""))
        if name in gate_names:
            failures.append(f"duplicate gate: {name}")
        gate_names.add(name)
        if gate.get("status") != "pass":
            failures.append(f"gate is not pass: {name}")
        if not HEX64.fullmatch(str(gate.get("evidence_sha256", ""))):
            failures.append(f"gate evidence digest invalid: {name}")
    missing_gates = sorted(REQUIRED_GATES - gate_names)
    extra_gates = sorted(gate_names - REQUIRED_GATES)
    if missing_gates or extra_gates:
        failures.append(
            f"gate set differs: missing={missing_gates}, extra={extra_gates}"
        )
    if len(str(release.get("smoke_response", "")).strip()) < 3:
        failures.append("smoke_response must be nonempty")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    release = json.loads(args.release.read_text(encoding="utf-8"))
    failures = validate_release(release)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        f"PASS: {release['release_id']} is immutable, compatible, and "
        f"contains all {len(REQUIRED_GATES)} required passing gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
