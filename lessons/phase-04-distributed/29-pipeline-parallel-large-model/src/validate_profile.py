#!/usr/bin/env python3
"""Fail-fast validation for the lesson-29 model/runtime profile."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"missing required environment variable {name}")
    return value


def numeric(name: str) -> float:
    value = required(name)
    try:
        number = float(value)
    except ValueError as error:
        raise SystemExit(f"{name} must be numeric, found {value!r}") from error
    if not math.isfinite(number) or number <= 0:
        raise SystemExit(f"{name} must be positive")
    return number


def positive_integer(
    name: str,
    *,
    minimum: int = 1,
    maximum: int,
) -> int:
    value = required(name)
    if not value.isdigit():
        raise SystemExit(f"{name} must be an integer, found {value!r}")
    number = int(value)
    if not minimum <= number <= maximum:
        raise SystemExit(
            f"{name} must be from {minimum} through {maximum}"
        )
    return number


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model_id = required("MODEL_ID")
    revision = required("MODEL_REVISION")
    served_name = required("SERVED_MODEL_NAME")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise SystemExit("MODEL_REVISION must be a 40- or 64-hex commit")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]+", model_id):
        raise SystemExit("MODEL_ID contains unsupported characters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", served_name):
        raise SystemExit("SERVED_MODEL_NAME contains unsupported characters")

    weight_gib = numeric("MODEL_TOTAL_WEIGHT_GIB")
    vram_gib = numeric("GPU_VRAM_GIB")
    overhead_gib = numeric("RUNTIME_OVERHEAD_GIB")
    try:
        reserve = float(required("VRAM_RESERVE_FRACTION"))
    except ValueError as error:
        raise SystemExit("VRAM_RESERVE_FRACTION must be numeric") from error
    if not math.isfinite(reserve) or not 0.05 <= reserve <= 0.30:
        raise SystemExit("VRAM_RESERVE_FRACTION must be between 0.05 and 0.30")
    max_model_len = positive_integer("MAX_MODEL_LEN", maximum=8192)
    max_num_seqs = positive_integer("MAX_NUM_SEQS", maximum=16)
    cache_gib = positive_integer(
        "MODEL_CACHE_GIB",
        minimum=5,
        maximum=500,
    )
    expected_versions = {
        "VLLM_EXPECTED_VERSION": "0.28.0",
        "RAY_EXPECTED_VERSION": "2.59.0",
    }
    versions = {}
    for name, expected in expected_versions.items():
        versions[name] = required(name)
        if versions[name] != expected:
            raise SystemExit(
                f"this draft pins {name}={expected}, found {versions[name]}"
            )
    large_mode = required("REQUIRE_LARGER_THAN_ONE_GPU").lower()
    if large_mode not in {"true", "false"}:
        raise SystemExit(
            "REQUIRE_LARGER_THAN_ONE_GPU must be true or false"
        )
    quantization = os.environ.get("QUANTIZATION", "")
    if quantization and not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}",
        quantization,
    ):
        raise SystemExit("QUANTIZATION contains unsupported characters")

    safe_single = vram_gib * (1 - reserve) - overhead_gib
    estimated_stage = weight_gib / 3 + overhead_gib
    safe_limit = vram_gib * (1 - reserve)
    larger_than_one = weight_gib > safe_single
    per_stage_fits = estimated_stage < safe_limit
    require_large = large_mode == "true"
    reasons = []
    if require_large and not larger_than_one:
        reasons.append(
            "profile claims large mode but weights do not exceed one safe GPU"
        )
    if not per_stage_fits:
        reasons.append("screened per-stage weight + overhead exceeds safe VRAM")

    document = {
        "schema_version": 1,
        "experiment_id": "lesson-29-profile",
        "strategy": "pipeline-parallel",
        "correctness": {"passed": not reasons},
        "environment": {
            "model_id": model_id,
            "model_revision": revision,
            "served_model_name": served_name,
            "quantization": quantization or None,
            "vllm_expected_version": versions["VLLM_EXPECTED_VERSION"],
            "ray_expected_version": versions["RAY_EXPECTED_VERSION"],
            "tp": 1,
            "pp": 3,
        },
        "measurements": {
            "weight_gib": weight_gib,
            "safe_single_gpu_weight_budget_gib": safe_single,
            "estimated_weight_plus_overhead_gib_per_stage": estimated_stage,
            "safe_vram_limit_gib": safe_limit,
            "larger_than_one_safe_gpu": larger_than_one,
            "estimated_per_stage_fits": per_stage_fits,
            "max_model_len": max_model_len,
            "max_num_seqs": max_num_seqs,
            "cache_gib_per_node": cache_gib,
        },
        "reasons": reasons,
        "limitations": [
            "stored weight GiB is not exact runtime tensor memory",
            "KV cache and architecture-specific stage imbalance require live measurement",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; passed={not reasons}")
    return 0 if not reasons else 2


if __name__ == "__main__":
    raise SystemExit(main())
