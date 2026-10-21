#!/usr/bin/env python3
"""Validate experimental consistency and compare three strategy records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dp", type=Path, required=True)
    parser.add_argument("--tp", type=Path, required=True)
    parser.add_argument("--pp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (args.dp, args.tp, args.pp)
    ]
    expected = {
        "data-parallel",
        "tensor-parallel",
        "pipeline-parallel",
    }
    strategies = {item["strategy"] for item in records}
    fields = {
        "workload_fingerprints": [
            item["environment"]["workload_sha256"] for item in records
        ],
        "model_revisions": [
            item["environment"]["model_revision"] for item in records
        ],
        "image_digests": [
            item["environment"]["image_digest"] for item in records
        ],
        "vllm_observed_versions": [
            item["environment"]["vllm_observed_version"]
            for item in records
        ],
        "ray_observed_versions": [
            item["environment"]["ray_observed_version"]
            for item in records
        ],
        "model_ids": [item["environment"]["model_id"] for item in records],
        "request_counts": [
            item["environment"]["request_count"] for item in records
        ],
        "concurrencies": [
            item["environment"]["concurrency"] for item in records
        ],
    }
    mismatches = [
        name for name, values in fields.items() if len(set(values)) != 1
    ]
    passed = (
        strategies == expected
        and not mismatches
        and all(item["correctness"]["passed"] for item in records)
    )
    by_strategy = {item["strategy"]: item["measurements"] for item in records}
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-30-comparison",
        "strategy": "capstone",
        "correctness": {"passed": passed},
        "environment": fields,
        "measurements": {
            "strategies": sorted(strategies),
            "by_strategy": by_strategy,
        },
        "mismatches": mismatches,
        "limitations": sorted(
            {
                limitation
                for item in records
                for limitation in item.get("limitations", [])
            }
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# DP / TP / PP comparison",
        "",
        f"- Consistency and correctness gate: `{passed}`",
        f"- Mismatched fields: `{mismatches}`",
        "",
        "| strategy | median E2E s | p90 E2E s | requests/s |",
        "|---|---:|---:|---:|",
    ]
    for strategy in sorted(by_strategy):
        values = by_strategy[strategy]
        lines.append(
            f"| {strategy} | "
            f"{values['latency_seconds']['median']:.4f} | "
            f"{values['latency_seconds']['p90_nearest_rank']:.4f} | "
            f"{values['requests_per_second']:.4f} |"
        )
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote comparison; passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
