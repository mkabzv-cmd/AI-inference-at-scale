#!/usr/bin/env python3
"""Small local Ray task/actor orientation with JSON evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import ray


@ray.remote
def square(value: int) -> int:
    return value * value


@ray.remote
class Counter:
    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> int:
        self.value += 1
        return self.value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ray.init(num_cpus=3, include_dashboard=False)
    squares = ray.get([square.remote(item) for item in range(4)])
    counter = Counter.remote()
    counter_values = ray.get([counter.increment.remote() for _ in range(3)])
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-26-local",
        "strategy": "ray-placement",
        "correctness": {
            "passed": squares == [0, 1, 4, 9]
            and counter_values == [1, 2, 3]
        },
        "environment": {
            "ray_version": ray.__version__,
            "cluster_resources": ray.cluster_resources(),
        },
        "measurements": {
            "task_results": squares,
            "actor_state_sequence": counter_values,
        },
        "limitations": [
            "single-process local Ray is not a multi-host placement test"
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ray.shutdown()
    print(f"wrote {args.output}")
    return 0 if document["correctness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
