#!/usr/bin/env python3
"""Create a frozen study specification from explicit environment inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"set {name}")
    return value


def bounded_integer(name: str, minimum: int, maximum: int) -> int:
    value = required(name)
    if not value.isdigit() or not minimum <= int(value) <= maximum:
        raise SystemExit(
            f"{name} must be an integer from {minimum} through {maximum}"
        )
    return int(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = args.workload.read_bytes()
    cases = []
    for line_number, line in enumerate(payload.splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(
                f"workload line {line_number} is invalid JSON: {error}"
            ) from error
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("case"), str)
            or not case["case"]
            or not isinstance(case.get("body"), dict)
        ):
            raise SystemExit(
                f"workload line {line_number} needs a nonempty case and body object"
            )
        cases.append(case)
    if not cases:
        raise SystemExit("workload must contain at least one case")
    if len({case["case"] for case in cases}) != len(cases):
        raise SystemExit("workload case names must be unique")
    image = required("VLLM_IMAGE")
    if not re.fullmatch(
        r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}", image
    ):
        raise SystemExit("VLLM_IMAGE must be a complete immutable digest")
    revision = required("MODEL_REVISION")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise SystemExit("MODEL_REVISION must be an immutable commit")
    try:
        price = float(required("PRICE_PER_NODE_HOUR"))
        repeats = int(required("REPEATS"))
        concurrency = int(required("BENCHMARK_CONCURRENCY"))
    except ValueError as error:
        raise SystemExit(
            "price, repeats, and concurrency must be numeric"
        ) from error
    if (
        not math.isfinite(price)
        or price <= 0
        or not 2 <= repeats <= 10
        or not 1 <= concurrency <= 16
    ):
        raise SystemExit("price > 0, repeats 2..10, concurrency 1..16 required")
    versions = {
        "vllm_expected_version": required("VLLM_EXPECTED_VERSION"),
        "ray_expected_version": required("RAY_EXPECTED_VERSION"),
        "kuberay_chart_version": required("KUBERAY_CHART_VERSION"),
    }
    pins = {
        "vllm_expected_version": "0.28.0",
        "ray_expected_version": "2.59.0",
        "kuberay_chart_version": "1.7.0",
    }
    if versions != pins:
        raise SystemExit(
            f"this draft requires exact software pins {pins}, found {versions}"
        )
    study_id = required("STUDY_ID")
    model_id = required("MODEL_ID")
    served_name = required("SERVED_MODEL_NAME")
    instance_type = required("NODE_INSTANCE_TYPE")
    currency = required("PRICE_CURRENCY")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", study_id):
        raise SystemExit("STUDY_ID contains unsupported characters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", model_id):
        raise SystemExit("MODEL_ID contains unsupported characters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", served_name):
        raise SystemExit("SERVED_MODEL_NAME contains unsupported characters")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", instance_type):
        raise SystemExit("NODE_INSTANCE_TYPE contains unsupported characters")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise SystemExit("PRICE_CURRENCY must be a three-letter uppercase code")
    runtime = {
        "max_model_len": bounded_integer(
            "MAX_MODEL_LEN",
            1,
            1_000_000,
        ),
        "max_num_seqs": bounded_integer(
            "MAX_NUM_SEQS",
            1,
            100_000,
        ),
        "model_cache_gib_per_node": bounded_integer(
            "MODEL_CACHE_GIB",
            5,
            500,
        ),
    }

    document = {
        "schema_version": 1,
        "study_id": study_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": model_id,
            "revision": revision,
            "served_name": served_name,
        },
        "software": {
            "image": image,
            "image_digest": image.rsplit("@", 1)[1],
            **versions,
        },
        "topology": {
            "node_count": 3,
            "gpus_per_node": 1,
            "instance_type": instance_type,
            "assumed_interconnect": (
                "ordinary cluster networking; verify transport from logs"
            ),
        },
        "workload": {
            "path": str(args.workload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "case_count": len(cases),
            "concurrency": concurrency,
            "warmup_rounds": 1,
        },
        "runtime": runtime,
        "design": {
            "repeats": repeats,
            "strategies": {
                "data-parallel": {"dp": 3, "tp": 1, "pp": 1},
                "tensor-parallel": {"dp": 1, "tp": 3, "pp": 1},
                "pipeline-parallel": {"dp": 1, "tp": 1, "pp": 3},
            },
        },
        "cost_assumption": {
            "price_per_node_hour": price,
            "currency": currency,
            "excluded": [
                "EKS control plane",
                "storage",
                "data transfer",
                "discounts and taxes",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
