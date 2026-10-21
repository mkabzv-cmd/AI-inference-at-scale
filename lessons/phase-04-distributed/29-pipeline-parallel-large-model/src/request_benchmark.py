#!/usr/bin/env python3
"""Small bounded HTTP completion benchmark with machine-readable output."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 < fraction <= 1:
        raise ValueError("nearest-rank fraction must be in (0, 1]")
    ordered = sorted(values)
    index = math.ceil(fraction * len(ordered)) - 1
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18029/v1/completions")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=6)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.requests <= 30 or not 1 <= args.concurrency <= 8:
        raise SystemExit("safety cap: requests 1..30 and concurrency 1..8")
    payload = args.request.read_bytes()

    def one(index: int) -> dict[str, object]:
        request = Request(
            args.url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urlopen(request, timeout=args.timeout) as response:
            document = json.load(response)
        elapsed = time.perf_counter() - started
        text = document["choices"][0]["text"]
        return {
            "index": index,
            "seconds": elapsed,
            "nonempty": bool(text),
            "completion_tokens": document.get("usage", {}).get(
                "completion_tokens"
            ),
        }

    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        records = list(executor.map(one, range(args.requests)))
    wall_seconds = time.perf_counter() - wall_started
    latencies = [float(record["seconds"]) for record in records]
    passed = len(records) == args.requests and all(
        record["nonempty"] for record in records
    )
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-29-request-benchmark",
        "strategy": "pipeline-parallel",
        "correctness": {"passed": passed},
        "environment": {
            "concurrency": args.concurrency,
            "requested_requests": args.requests,
        },
        "measurements": {
            "successful_requests": len(records),
            "wall_seconds": wall_seconds,
            "requests_per_second": len(records) / wall_seconds,
            "latency_seconds": {
                "median": statistics.median(latencies),
                "p90_nearest_rank": percentile(latencies, 0.90),
                "maximum": max(latencies),
            },
            "records": records,
        },
        "limitations": [
            "non-streaming end-to-end latency only",
            "TTFT and token-level TPOT are not measured",
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
