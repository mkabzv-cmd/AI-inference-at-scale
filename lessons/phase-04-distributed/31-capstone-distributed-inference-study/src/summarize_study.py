#!/usr/bin/env python3
"""Validate comparability and summarize repeated strategy runs."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


STRATEGIES = (
    "data-parallel",
    "tensor-parallel",
    "pipeline-parallel",
)


def load_runs(path: Path | None, directory: Path | None) -> list[dict[str, Any]]:
    if path:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else [value]
    assert directory is not None
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(directory.glob("*.json"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--runs", type=Path)
    group.add_argument("--runs-dir", type=Path)
    parser.add_argument("--cost", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    runs = load_runs(args.runs, args.runs_dir)
    expected_repeats = spec["design"]["repeats"]
    comparison_fields = (
        "model_id",
        "model_revision",
        "image_digest",
        "workload_sha256",
        "request_count",
        "concurrency",
        "instance_type",
        "vllm_expected_version",
        "ray_expected_version",
        "vllm_observed_version",
        "ray_observed_version",
        "max_model_len",
        "max_num_seqs",
        "model_cache_gib_per_node",
    )
    cross_run_mismatches = [
        field
        for field in comparison_fields
        if len({run["environment"][field] for run in runs}) != 1
    ]
    frozen_environment = {
        "model_id": spec["model"]["id"],
        "model_revision": spec["model"]["revision"],
        "image_digest": spec["software"]["image_digest"],
        "workload_sha256": spec["workload"]["sha256"],
        "request_count": spec["workload"]["case_count"],
        "concurrency": spec["workload"]["concurrency"],
        "instance_type": spec["topology"]["instance_type"],
        "vllm_expected_version": spec["software"][
            "vllm_expected_version"
        ],
        "ray_expected_version": spec["software"]["ray_expected_version"],
        "vllm_observed_version": spec["software"][
            "vllm_expected_version"
        ],
        "ray_observed_version": spec["software"]["ray_expected_version"],
        "max_model_len": spec["runtime"]["max_model_len"],
        "max_num_seqs": spec["runtime"]["max_num_seqs"],
        "model_cache_gib_per_node": spec["runtime"][
            "model_cache_gib_per_node"
        ],
    }
    frozen_input_mismatches = {
        field: {
            "expected": expected,
            "observed": sorted(
                {
                    run["environment"][field]
                    for run in runs
                    if run["environment"][field] != expected
                },
                key=str,
            ),
        }
        for field, expected in frozen_environment.items()
        if any(
            run["environment"][field] != expected for run in runs
        )
    }
    by_strategy: dict[str, list[dict[str, Any]]] = {
        strategy: [] for strategy in STRATEGIES
    }
    unknown_strategies = sorted(
        {
            str(run.get("strategy"))
            for run in runs
            if run.get("strategy") not in by_strategy
        }
    )
    for run in runs:
        if run["strategy"] in by_strategy:
            by_strategy[run["strategy"]].append(run)
    repetition_counts = {
        name: len(values) for name, values in by_strategy.items()
    }
    repetition_sets = {
        name: sorted(int(run["repetition"]) for run in values)
        for name, values in by_strategy.items()
    }
    expected_repetition_set = list(range(1, expected_repeats + 1))
    study_id_mismatches = sorted(
        {
            str(run.get("study_id"))
            for run in runs
            if run.get("study_id") != spec["study_id"]
        }
    )
    duplicate_ids = len({run["experiment_id"] for run in runs}) != len(runs)
    expected_run_count = len(STRATEGIES) * expected_repeats
    passed = (
        not cross_run_mismatches
        and not frozen_input_mismatches
        and not unknown_strategies
        and not study_id_mismatches
        and not duplicate_ids
        and len(runs) == expected_run_count
        and all(run["correctness"]["passed"] for run in runs)
        and all(
            repetitions == expected_repetition_set
            for repetitions in repetition_sets.values()
        )
    )
    summaries = {}
    for strategy, values in by_strategy.items():
        rates = [
            float(run["measurements"]["requests_per_second"])
            for run in values
        ]
        latencies = [
            float(run["measurements"]["median_end_to_end_seconds"])
            for run in values
        ]
        if values:
            summaries[strategy] = {
                "runs": len(values),
                "requests_per_second": {
                    "median": statistics.median(rates),
                    "minimum": min(rates),
                    "maximum": max(rates),
                },
                "median_end_to_end_seconds_across_runs": {
                    "median": statistics.median(latencies),
                    "minimum": min(latencies),
                    "maximum": max(latencies),
                },
            }
    cost = (
        json.loads(args.cost.read_text(encoding="utf-8"))
        if args.cost
        else {"not_supplied": True}
    )
    document = {
        "schema_version": 1,
        "experiment_id": f"{spec['study_id']}-summary",
        "strategy": "capstone",
        "correctness": {"passed": passed},
        "environment": {
            "study_id": spec["study_id"],
            "comparison_fields": {
                field: sorted(
                    {run["environment"][field] for run in runs},
                    key=str,
                )
                for field in comparison_fields
            },
        },
        "measurements": {
            "strategies": list(STRATEGIES),
            "repetitions_per_strategy": min(repetition_counts.values()),
            "repetition_counts": repetition_counts,
            "by_strategy": summaries,
        },
        "cost": cost,
        "diagnostics": {
            "mismatched_fields": sorted(
                set(cross_run_mismatches) | set(frozen_input_mismatches)
            ),
            "cross_run_mismatches": cross_run_mismatches,
            "frozen_input_mismatches": frozen_input_mismatches,
            "unknown_strategies": unknown_strategies,
            "duplicate_experiment_ids": duplicate_ids,
            "expected_repeats": expected_repeats,
            "expected_run_count": expected_run_count,
            "observed_run_count": len(runs),
            "expected_repetition_set": expected_repetition_set,
            "observed_repetition_sets": repetition_sets,
            "study_id_mismatches": study_id_mismatches,
        },
        "limitations": sorted(
            {
                limitation
                for run in runs
                for limitation in run.get("limitations", [])
            }
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Distributed-inference study summary",
        "",
        f"- Study: `{spec['study_id']}`",
        f"- Evidence gate: `{passed}`",
        f"- Repetition counts: `{repetition_counts}`",
        f"- Cross-run mismatches: `{cross_run_mismatches}`",
        f"- Frozen-input mismatches: `{sorted(frozen_input_mismatches)}`",
        f"- Unknown strategies: `{unknown_strategies}`",
        "",
        "| strategy | runs | median req/s | median run-median E2E s |",
        "|---|---:|---:|---:|",
    ]
    for strategy in STRATEGIES:
        value = summaries.get(strategy)
        if value:
            lines.append(
                f"| {strategy} | {value['runs']} | "
                f"{value['requests_per_second']['median']:.4f} | "
                f"{value['median_end_to_end_seconds_across_runs']['median']:.4f} |"
            )
        else:
            lines.append(f"| {strategy} | 0 | — | — |")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
