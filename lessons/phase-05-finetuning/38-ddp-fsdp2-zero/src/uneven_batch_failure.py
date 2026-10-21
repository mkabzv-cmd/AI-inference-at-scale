#!/usr/bin/env python3
"""Show why averaging rank means biases uneven local batch sizes."""

import argparse
import json
from pathlib import Path


def gradient(weight, rows):
    return sum((weight * x - y) * x for x, y in rows) / len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    weight = 0.25
    batches = [
        [(1.0, 2.0)],
        [(2.0, 4.0), (3.0, 6.0)],
        [(4.0, 8.0), (5.0, 10.0), (6.0, 12.0)],
    ]
    rank_means = [gradient(weight, rows) for rows in batches]
    naive_rank_mean = sum(rank_means) / len(rank_means)
    all_rows = [row for batch in batches for row in batch]
    true_sample_mean = gradient(weight, all_rows)
    difference = abs(naive_rank_mean - true_sample_mean)
    result = {
        "schema_version": 1,
        "rank_batch_sizes": [len(rows) for rows in batches],
        "naive_mean_of_rank_means": naive_rank_mean,
        "true_sample_weighted_mean": true_sample_mean,
        "absolute_difference": difference,
        "failure": "uneven rank batches make an unweighted rank mean biased"
    }
    assert difference > 0.1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    raise SystemExit(
        "expected failure: rank-local batch sizes differ, so DDP's "
        "unweighted rank mean is not the global sample mean"
    )


if __name__ == "__main__":
    main()
