#!/usr/bin/env python3
"""Validate immutable identifiers and bounded capstone design."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


def validate(path: Path) -> list[str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    if document.get("schema_version") != 1:
        failures.append("schema_version must equal 1")
    revision = document.get("model", {}).get("revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        failures.append("model revision is not immutable hexadecimal")
    digest = document.get("software", {}).get("image_digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        failures.append("image digest is not sha256:<64 hex>")
    software = document.get("software", {})
    image = software.get("image", "")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}",
        image,
    ):
        failures.append("software image is not an immutable digest reference")
    elif image.rsplit("@", 1)[1] != digest:
        failures.append("software image and image_digest disagree")
    expected_pins = {
        "vllm_expected_version": "0.28.0",
        "ray_expected_version": "2.59.0",
        "kuberay_chart_version": "1.7.0",
    }
    for field, expected_value in expected_pins.items():
        if software.get(field) != expected_value:
            failures.append(f"{field} must equal {expected_value}")
    topology = document.get("topology", {})
    if topology.get("node_count") != 3 or topology.get("gpus_per_node") != 1:
        failures.append("capstone topology must be three one-GPU nodes")
    repeats = document.get("design", {}).get("repeats", 0)
    if not 2 <= repeats <= 10:
        failures.append("repeats must be from 2 through 10")
    expected = {
        "data-parallel": (3, 1, 1),
        "tensor-parallel": (1, 3, 1),
        "pipeline-parallel": (1, 1, 3),
    }
    strategies = document.get("design", {}).get("strategies", {})
    for name, factors in expected.items():
        actual = strategies.get(name, {})
        if (actual.get("dp"), actual.get("tp"), actual.get("pp")) != factors:
            failures.append(f"{name} factors do not match {factors}")
    workload = document.get("workload", {})
    if not re.fullmatch(r"[0-9a-f]{64}", workload.get("sha256", "")):
        failures.append("workload SHA-256 is invalid")
    if not 1 <= workload.get("concurrency", 0) <= 16:
        failures.append("workload concurrency must be from 1 through 16")
    if not 1 <= workload.get("case_count", 0) <= 10_000:
        failures.append("workload case_count must be from 1 through 10000")
    if workload.get("warmup_rounds") != 1:
        failures.append("workload warmup_rounds must equal 1")
    runtime = document.get("runtime", {})
    for field, minimum, maximum in (
        ("max_model_len", 1, 1_000_000),
        ("max_num_seqs", 1, 100_000),
        ("model_cache_gib_per_node", 5, 500),
    ):
        value = runtime.get(field)
        if not isinstance(value, int) or not minimum <= value <= maximum:
            failures.append(
                f"runtime {field} must be from {minimum} through {maximum}"
            )
    cost = document.get("cost_assumption", {})
    price = cost.get("price_per_node_hour")
    if (
        not isinstance(price, (int, float))
        or not math.isfinite(price)
        or price <= 0
    ):
        failures.append("price_per_node_hour must be positive and finite")
    if not re.fullmatch(r"[A-Z]{3}", str(cost.get("currency", ""))):
        failures.append("cost currency must be a three-letter uppercase code")
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} STUDY_SPEC.json")
    failures = validate(Path(sys.argv[1]))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("study specification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
