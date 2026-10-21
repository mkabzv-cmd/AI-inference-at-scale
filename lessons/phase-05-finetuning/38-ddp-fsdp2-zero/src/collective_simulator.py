#!/usr/bin/env python3
"""Dependency-free DDP and sharded-collective correctness reference."""

import argparse
import json
from pathlib import Path


def gradient(weight, rows):
    return sum((weight * x - y) * x for x, y in rows) / len(rows)


def flatten(shards):
    return [value for shard in shards for value in shard]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    weight = -0.75
    learning_rate = 0.05
    rank_batches = [
        [(1.0, 2.0), (2.0, 4.0)],
        [(3.0, 6.0), (4.0, 8.0)],
        [(5.0, 10.0), (6.0, 12.0)],
    ]
    rank_gradients = [gradient(weight, rows) for rows in rank_batches]
    all_reduce_mean = sum(rank_gradients) / len(rank_gradients)
    global_gradient = gradient(weight, flatten(rank_batches))
    ddp_weight = weight - learning_rate * all_reduce_mean
    single_weight = weight - learning_rate * global_gradient

    tensor = list(range(12))
    reduce_scatter_inputs = [
        [value + rank for value in tensor] for rank in range(3)
    ]
    elementwise_sum = [
        sum(row[index] for row in reduce_scatter_inputs)
        for index in range(len(tensor))
    ]
    shard_width = len(tensor) // 3
    reduced_shards = [
        elementwise_sum[index * shard_width : (index + 1) * shard_width]
        for index in range(3)
    ]
    all_gathered = flatten(reduced_shards)

    report = {
        "schema_version": 1,
        "world_size": 3,
        "equal_local_batch_sizes": True,
        "rank_gradients": rank_gradients,
        "all_reduce_mean_gradient": all_reduce_mean,
        "single_process_global_mean_gradient": global_gradient,
        "ddp_weight_after_update": ddp_weight,
        "single_process_weight_after_update": single_weight,
        "maximum_update_difference": abs(ddp_weight - single_weight),
        "reduce_scatter_shards": reduced_shards,
        "all_gather_reconstruction": all_gathered,
        "expected_elementwise_reduction": elementwise_sum,
    }
    assert report["maximum_update_difference"] < 1e-12
    assert all_gathered == elementwise_sum
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: equal-batch DDP mean equals the global mean; "
        "reduce-scatter plus all-gather reconstruction verified"
    )


if __name__ == "__main__":
    main()
