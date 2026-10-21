#!/usr/bin/env python3
"""Aggregate staged load, apply SLOs, and identify first saturation evidence."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil(percentile_value * len(ordered)) - 1,
        ),
    )
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in args.records.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    by_stage: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        by_stage[str(record["stage"])].append(record)

    summaries = []
    previous_throughput = None
    first_breach = None
    for stage in plan["stages"]:
        name = str(stage["name"])
        values = by_stage[name]
        elapsed = float(metadata["stage_elapsed_seconds"][name])
        successes = [item for item in values if item["status"] == 200]
        errors = len(values) - len(successes)
        ttft = [float(item["server_ttft_seconds"]) for item in successes]
        total = [float(item["client_total_seconds"]) for item in successes]
        queue = [float(item["server_queue_seconds"]) for item in successes]
        throughput = len(successes) / elapsed
        summary = {
            "stage": name,
            "concurrency": stage["concurrency"],
            "requests": len(values),
            "successes": len(successes),
            "errors": errors,
            "error_rate": errors / len(values),
            "elapsed_seconds": elapsed,
            "requests_per_second": throughput,
            "p50_queue_seconds": percentile(queue, 0.50),
            "p95_queue_seconds": percentile(queue, 0.95),
            "p50_ttft_seconds": percentile(ttft, 0.50),
            "p95_ttft_seconds": percentile(ttft, 0.95),
            "p50_total_seconds": percentile(total, 0.50),
            "p95_total_seconds": percentile(total, 0.95),
            "throughput_gain_from_previous": (
                None
                if previous_throughput is None
                else throughput / previous_throughput
            ),
        }
        slo = plan["slo"]
        failures = []
        if summary["error_rate"] > slo["maximum_error_rate"]:
            failures.append("error_rate")
        if summary["p95_ttft_seconds"] > slo["maximum_p95_ttft_seconds"]:
            failures.append("p95_ttft")
        if summary["p95_total_seconds"] > slo["maximum_p95_total_seconds"]:
            failures.append("p95_total")
        summary["slo_pass"] = not failures
        summary["slo_failures"] = failures
        if failures and first_breach is None:
            first_breach = name
        summaries.append(summary)
        previous_throughput = throughput

    payload = {
        "schema_version": 1,
        "stages": summaries,
        "first_slo_breach": first_breach,
        "interpretation": (
            "Queue and TTFT growth after service capacity is occupied are the "
            "simulator's first saturation evidence. Confirm real systems with "
            "engine, GPU, CPU, memory, and network telemetry."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for summary in summaries:
        print(
            f"{summary['stage']} rps={summary['requests_per_second']:.2f} "
            f"p95_ttft={summary['p95_ttft_seconds']:.3f} "
            f"slo_pass={summary['slo_pass']}"
        )
    print(f"first_slo_breach={first_breach}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
