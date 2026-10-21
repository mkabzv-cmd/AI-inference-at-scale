#!/usr/bin/env python3
"""Dependency-free proof that row-sharded products sum to the full product."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def matmul(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    return [
        [
            sum(left[row][k] * right[k][column] for k in range(len(right)))
            for column in range(len(right[0]))
        ]
        for row in range(len(left))
    ]


def add(*matrices: list[list[int]]) -> list[list[int]]:
    return [
        [
            sum(matrix[row][column] for matrix in matrices)
            for column in range(len(matrices[0][0]))
        ]
        for row in range(len(matrices[0]))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    hidden = [[1, 2, 3, 4, 5, 6]]
    weights = [
        [1, 0],
        [0, 1],
        [1, 1],
        [2, 0],
        [0, 2],
        [2, 2],
    ]
    full = matmul(hidden, weights)
    partials = [
        matmul([hidden[0][start : start + 2]], weights[start : start + 2])
        for start in (0, 2, 4)
    ]
    reduced = add(*partials)
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-28-arithmetic",
        "strategy": "toy-sharding",
        "correctness": {"passed": reduced == full},
        "environment": {"dependency_free": True},
        "measurements": {
            "full_output": full,
            "partial_outputs": partials,
            "reduced_output": reduced,
        },
        "limitations": ["integer fixture is not a performance benchmark"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; passed={reduced == full}")
    return 0 if reduced == full else 1


if __name__ == "__main__":
    raise SystemExit(main())
