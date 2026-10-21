#!/usr/bin/env python3
"""Comparable bounded benchmark for DP, TP, and PP."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import re
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


def nearest(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("nearest-rank percentile requires values")
    if not 0 < fraction <= 1:
        raise ValueError("nearest-rank fraction must be in (0, 1]")
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--vllm-version", required=True)
    parser.add_argument("--ray-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    allowed = {"data-parallel", "tensor-parallel", "pipeline-parallel"}
    if args.strategy not in allowed:
        raise SystemExit(f"strategy must be one of {sorted(allowed)}")
    if not 1 <= args.requests <= 60 or not 1 <= args.concurrency <= 12:
        raise SystemExit("safety caps: requests 1..60, concurrency 1..12")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.model_revision):
        raise SystemExit("model revision must be a 40- or 64-hex commit")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_digest):
        raise SystemExit("image digest must be sha256:<64 lowercase hex>")
    payload = args.request.read_bytes()
    fingerprint = hashlib.sha256(payload).hexdigest()

    def one(index: int) -> dict[str, object]:
        request = Request(
            args.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        with urlopen(request, timeout=180) as response:
            document = json.load(response)
        elapsed = time.perf_counter() - started
        return {
            "index": index,
            "seconds": elapsed,
            "valid": bool(document["choices"][0]["text"]),
            "completion_tokens": document.get("usage", {}).get(
                "completion_tokens"
            ),
        }

    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as pool:
        records = list(pool.map(one, range(args.requests)))
    wall = time.perf_counter() - wall_started
    latency = [float(item["seconds"]) for item in records]
    passed = len(records) == args.requests and all(
        item["valid"] for item in records
    )
    document = {
        "schema_version": 1,
        "experiment_id": f"lesson-30-{args.strategy}",
        "strategy": args.strategy,
        "correctness": {"passed": passed},
        "environment": {
            "model_id": args.model_id,
            "model_revision": args.model_revision,
            "image_digest": args.image_digest,
            "vllm_observed_version": args.vllm_version,
            "ray_observed_version": args.ray_version,
            "workload_sha256": fingerprint,
            "concurrency": args.concurrency,
            "request_count": args.requests,
            "fixture": False,
        },
        "measurements": {
            "wall_seconds": wall,
            "requests_per_second": len(records) / wall,
            "latency_seconds": {
                "median": statistics.median(latency),
                "p90_nearest_rank": nearest(latency, 0.9),
                "maximum": max(latency),
            },
            "records": records,
        },
        "limitations": [
            "non-streaming end-to-end latency; TTFT and TPOT not measured"
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
