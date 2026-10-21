#!/usr/bin/env python3
"""Aggregate repeated runs without hiding the raw observations."""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path
from typing import Any


def workload_label(item: dict[str, Any]) -> str:
    workload = item["workload"]
    if workload["mode"] == "closed":
        return f"closed-c{workload['concurrency']}"
    return f"open-rps{workload['request_rate']:g}"


def median(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return round(statistics.median(present), 3) if present else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    groups: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for path in sorted(args.directory.glob("*/*.json")):
        item = json.loads(path.read_text())
        groups[(item["engine"]["name"], workload_label(item))].append(item)
    aggregates = []
    for (engine, workload), runs in sorted(groups.items()):
        aggregates.append(
            {
                "engine": engine,
                "engine_version": runs[0]["engine"]["version"],
                "workload": workload,
                "repeats": len(runs),
                "median_request_throughput_per_second": median(
                    [run["summary"]["request_throughput_per_second"] for run in runs]
                ),
                "median_output_token_throughput_per_second": median(
                    [run["summary"]["output_token_throughput_per_second"] for run in runs]
                ),
                "median_p50_e2e_ms": median(
                    [run["summary"]["latency_ms"]["p50"] for run in runs]
                ),
                "median_p95_e2e_ms": median(
                    [run["summary"]["latency_ms"]["p95"] for run in runs]
                ),
                "median_p50_ttft_ms": median(
                    [run["summary"]["ttft_ms"]["p50"] for run in runs]
                ),
                "median_p50_tpot_ms": median(
                    [run["summary"]["tpot_ms"]["p50"] for run in runs]
                ),
                "minimum_quality_pass_rate": min(
                    run["summary"]["quality_pass_rate"] for run in runs
                ),
                "raw_run_ids": [run["run_id"] for run in runs],
            }
        )
    output = {
        "schema_version": "oms-engine-comparison/v1",
        "aggregation": "median of independent runs; quality uses minimum",
        "rows": aggregates,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(output, indent=2) + "\n")
    lines = [
        "# Controlled engine comparison",
        "",
        "| Engine | Workload | Repeats | req/s | output tok/s | p50 E2E ms | p95 E2E ms | p50 TTFT ms | p50 TPOT ms | Min quality |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregates:
        def show(name: str) -> str:
            value = row[name]
            return "n/a" if value is None else str(value)
        lines.append(
            f"| {row['engine']} | {row['workload']} | {row['repeats']} | "
            f"{show('median_request_throughput_per_second')} | "
            f"{show('median_output_token_throughput_per_second')} | "
            f"{show('median_p50_e2e_ms')} | {show('median_p95_e2e_ms')} | "
            f"{show('median_p50_ttft_ms')} | {show('median_p50_tpot_ms')} | "
            f"{row['minimum_quality_pass_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "Medians reduce sensitivity to one noisy run; they do not establish statistical "
            "significance. Inspect every raw request and explain variance before deciding.",
            "",
        ]
    )
    args.markdown_output.write_text("\n".join(lines))
    print(args.markdown_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
