#!/usr/bin/env python3
"""Find non-dominated measured configurations without inventing one score."""

import argparse
import json
import math
from pathlib import Path


def dominates(left, right):
    no_worse = (
        left["median_tokens_per_second"]
        >= right["median_tokens_per_second"]
        and left["peak_allocated_gib"] <= right["peak_allocated_gib"]
        and left["validation_loss"] <= right["validation_loss"]
    )
    strictly_better = (
        left["median_tokens_per_second"]
        > right["median_tokens_per_second"]
        or left["peak_allocated_gib"] < right["peak_allocated_gib"]
        or left["validation_loss"] < right["validation_loss"]
    )
    return no_worse and strictly_better


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    runs = source["runs"]
    names = [str(row["name"]) for row in runs]
    if len(runs) < 2 or len(names) != len(set(names)):
        raise SystemExit("results need at least two uniquely named runs")
    metric_names = (
        "median_tokens_per_second",
        "peak_allocated_gib",
        "validation_loss",
    )
    for row in runs:
        for metric in metric_names:
            value = float(row[metric])
            if not math.isfinite(value):
                raise SystemExit(f"{row['name']}: {metric} must be finite")
        if (
            float(row["median_tokens_per_second"]) <= 0
            or float(row["peak_allocated_gib"]) < 0
            or float(row["validation_loss"]) < 0
        ):
            raise SystemExit(
                f"{row['name']}: throughput must be positive and "
                "memory/loss nonnegative"
            )
    if any(row["measured_optimizer_steps"] < 30 for row in runs):
        raise SystemExit("every result needs at least 30 measured optimizer steps")
    frontier = [
        row["name"]
        for row in runs
        if not any(
            dominates(other, row)
            for other in runs
            if other["name"] != row["name"]
        )
    ]
    dominated = sorted(
        row["name"] for row in runs if row["name"] not in frontier
    )
    report = {
        "schema_version": 1,
        "source_evidence_kind": source["evidence_kind"],
        "pareto_frontier": sorted(frontier),
        "dominated": dominated,
        "selection_required": (
            "Choose from the frontier using a predeclared memory, throughput, "
            "quality, and cost constraint; the analyzer does not crown a winner."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"PASS: frontier={','.join(sorted(frontier))}; "
        f"dominated={','.join(dominated)}"
    )


if __name__ == "__main__":
    main()
