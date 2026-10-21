#!/usr/bin/env python3
"""Compare materialized attention with online-softmax tiled attention.

This is a tiny CPU reference implementation. It demonstrates the recurrence
that lets FlashAttention-style algorithms avoid materializing the full score
matrix in high-bandwidth memory. It is not a GPU kernel or speed benchmark.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def materialized_attention(
    query: list[list[float]],
    key: list[list[float]],
    value: list[list[float]],
) -> list[list[float]]:
    scale = 1 / math.sqrt(len(query[0]))
    output = []
    for query_row in query:
        scores = [dot(query_row, key_row) * scale for key_row in key]
        maximum = max(scores)
        exponents = [math.exp(score - maximum) for score in scores]
        denominator = sum(exponents)
        probabilities = [item / denominator for item in exponents]
        output.append(
            [
                sum(
                    probability * value[row][column]
                    for row, probability in enumerate(probabilities)
                )
                for column in range(len(value[0]))
            ]
        )
    return output


def online_tiled_attention(
    query: list[list[float]],
    key: list[list[float]],
    value: list[list[float]],
    tile_k: int,
) -> list[list[float]]:
    scale = 1 / math.sqrt(len(query[0]))
    outputs = []
    for query_row in query:
        running_max = -math.inf
        running_denominator = 0.0
        running_numerator = [0.0 for _ in value[0]]
        for start in range(0, len(key), tile_k):
            keys = key[start : start + tile_k]
            values = value[start : start + tile_k]
            scores = [dot(query_row, key_row) * scale for key_row in keys]
            tile_max = max(scores)
            new_max = max(running_max, tile_max)
            previous_rescale = (
                0.0
                if running_max == -math.inf
                else math.exp(running_max - new_max)
            )
            running_denominator *= previous_rescale
            running_numerator = [
                item * previous_rescale for item in running_numerator
            ]
            for score, value_row in zip(scores, values):
                probability_numerator = math.exp(score - new_max)
                running_denominator += probability_numerator
                for column, item in enumerate(value_row):
                    running_numerator[column] += probability_numerator * item
            running_max = new_max
        outputs.append(
            [item / running_denominator for item in running_numerator]
        )
    return outputs


def max_difference(
    left: list[list[float]], right: list[list[float]]
) -> float:
    return max(
        abs(a - b)
        for left_row, right_row in zip(left, right)
        for a, b in zip(left_row, right_row)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-tokens", type=int, default=8)
    parser.add_argument("--kv-tokens", type=int, default=11)
    parser.add_argument("--head-dim", type=int, default=4)
    parser.add_argument("--tile-k", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2020)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.query_tokens, args.kv_tokens, args.head_dim, args.tile_k) <= 0:
        parser.error("shape and tile dimensions must be positive")
    rng = random.Random(args.seed)
    query = [
        [rng.uniform(-1, 1) for _ in range(args.head_dim)]
        for _ in range(args.query_tokens)
    ]
    key = [
        [rng.uniform(-1, 1) for _ in range(args.head_dim)]
        for _ in range(args.kv_tokens)
    ]
    value = [
        [rng.uniform(-1, 1) for _ in range(args.head_dim)]
        for _ in range(args.kv_tokens)
    ]
    materialized = materialized_attention(query, key, value)
    online = online_tiled_attention(query, key, value, args.tile_k)
    difference = max_difference(materialized, online)
    result = {
        "schema_version": "oms-online-attention-reference/v1",
        "result_kind": "cpu_reference_correctness_not_performance",
        "shape": {
            "query": [args.query_tokens, args.head_dim],
            "key": [args.kv_tokens, args.head_dim],
            "value": [args.kv_tokens, args.head_dim],
        },
        "tile_k": args.tile_k,
        "full_score_elements": args.query_tokens * args.kv_tokens,
        "peak_score_elements_per_query_in_tiled_loop": min(
            args.tile_k, args.kv_tokens
        ),
        "max_absolute_output_difference": difference,
        "tolerance": 1e-12,
        "passed": difference <= 1e-12,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
