#!/usr/bin/env python3
"""Collect RESULT_JSON events from one log file per distributed rank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-world-size", type=int, default=3)
    return parser.parse_args()


def read_record(path: Path) -> dict[str, Any]:
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "RESULT_JSON":
            event.pop("event", None)
            matches.append(event)
    if len(matches) != 1:
        raise ValueError(
            f"{path} contains {len(matches)} RESULT_JSON records"
        )
    return matches[0]


def main() -> int:
    args = parse_args()
    records = [
        read_record(path) for path in sorted(args.logs.glob("*.log"))
    ]
    ranks = {item["rank"] for item in records}
    pod_hostnames = {item["hostname"] for item in records}
    passed = (
        len(records) == args.expect_world_size
        and ranks == set(range(args.expect_world_size))
        and len(pod_hostnames) == args.expect_world_size
        and all(item["correctness"]["passed"] for item in records)
    )
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-24-kubernetes",
        "strategy": "collective",
        "correctness": {"passed": passed},
        "environment": {
            "world_size": args.expect_world_size,
            "distinct_pod_hostnames": len(pod_hostnames),
            "backends": sorted({item["backend"] for item in records}),
        },
        "measurements": {
            "rank_median_ms": {
                str(item["rank"]): item["timing_ms"]["median"]
                for item in records
            }
        },
        "ranks": sorted(records, key=lambda item: item["rank"]),
        "limitations": [
            "Pod hostnames identify Pods, not physical Kubernetes nodes",
            "join this record with pod-placement.txt before claiming "
            "distinct-node placement",
            "Pod logs are learner-collected evidence, not an independently "
            "validated run",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; correctness={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
