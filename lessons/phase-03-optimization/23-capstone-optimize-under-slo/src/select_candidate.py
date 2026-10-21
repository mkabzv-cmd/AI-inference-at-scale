#!/usr/bin/env python3
"""Apply hard gates, then select a winner by the declared objective."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(candidate: dict[str, Any], slo: dict[str, Any]) -> dict[str, Any]:
    failures = []
    checks = [
        (
            candidate["success_rate"] >= slo["minimum_success_rate"],
            "success_rate",
        ),
        (
            candidate["quality_pass_rate"]
            >= slo["minimum_quality_pass_rate"],
            "quality_pass_rate",
        ),
        (
            candidate["ttft_p95_ms"] <= slo["maximum_ttft_p95_ms"],
            "ttft_p95_ms",
        ),
        (
            candidate["e2e_p95_ms"] <= slo["maximum_e2e_p95_ms"],
            "e2e_p95_ms",
        ),
        (
            candidate["output_throughput_tokens_per_second"]
            >= slo["minimum_output_throughput_tokens_per_second"],
            "output_throughput_tokens_per_second",
        ),
        (
            candidate["peak_gpu_memory_gib"]
            <= slo["maximum_peak_gpu_memory_gib"],
            "peak_gpu_memory_gib",
        ),
    ]
    failures.extend(name for passed, name in checks if not passed)
    return {**candidate, "feasible": not failures, "failed_gates": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slo", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    slo = load(args.slo)
    result_set = load(args.results)
    evaluated = [
        evaluate(candidate, slo) for candidate in result_set["candidates"]
    ]
    feasible = [candidate for candidate in evaluated if candidate["feasible"]]
    winner = (
        max(
            feasible,
            key=lambda item: item[
                "output_throughput_tokens_per_second"
            ],
        )["id"]
        if feasible
        else None
    )
    output = {
        "schema_version": "oms-capstone-selection/v1",
        "result_kind": result_set["result_kind"],
        "slo": slo,
        "evaluated_candidates": evaluated,
        "winner": winner,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for candidate in evaluated:
        print(
            f"{candidate['id']:<22} feasible={candidate['feasible']} "
            f"failed={','.join(candidate['failed_gates']) or '-'}"
        )
    print("winner:", winner or "none")
    return 0 if winner else 3


if __name__ == "__main__":
    raise SystemExit(main())
