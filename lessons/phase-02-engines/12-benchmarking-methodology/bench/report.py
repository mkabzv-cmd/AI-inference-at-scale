#!/usr/bin/env python3
"""Convert one or more benchmark JSON records into a compact Markdown report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def value(item: object, suffix: str = "") -> str:
    if item is None:
        return "n/a"
    if isinstance(item, float):
        return f"{item:.3f}{suffix}"
    return f"{item}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = []
    provenance = []
    for path in args.results:
        data = json.loads(path.read_text())
        summary = data["summary"]
        rows.append(
            [
                data["engine"]["name"],
                data["engine"]["version"],
                data["workload"]["mode"],
                str(data["workload"]["concurrency"]),
                value(summary["request_throughput_per_second"]),
                value(summary["output_token_throughput_per_second"]),
                value(summary["latency_ms"]["p50"]),
                value(summary["latency_ms"]["p95"]),
                value(summary["ttft_ms"]["p50"]),
                value(summary["tpot_ms"]["p50"]),
                f"{summary['quality_pass_rate']:.1%}",
            ]
        )
        provenance.append(
            f"- `{path}` — run `{data['run_id']}`, prompt set "
            f"`{data['workload']['prompt_set_sha256']}`, server "
            f"`{data['environment']['server_fingerprint']}`"
        )
    lines = [
        "# Benchmark report",
        "",
        "| Engine | Version | Mode | C | req/s | output tok/s | p50 E2E ms | p95 E2E ms | p50 TTFT ms | p50 TPOT ms | Quality |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Describe the workload, uncertainty, saturation point, correctness failures, "
            "and mechanism behind each material difference. Do not crown a winner from "
            "one run.",
            "",
            "## Provenance",
            "",
            *provenance,
            "",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
