#!/usr/bin/env python3
"""Extract benchmark records from logs and produce JSON plus Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def extract(directory: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(directory.glob("*.log")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.pop("event", None) == "BENCHMARK_RESULT":
                event["source_log"] = path.name
                records.append(event)
    return sorted(
        records, key=lambda item: (item["operation"], item["message_bytes"])
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()

    records = extract(args.logs)
    world_sizes = {item["world_size"] for item in records}
    expected_operations = {"all-reduce", "all-to-all", "ping-pong"}
    operations = {item["operation"] for item in records}
    pairs = [
        (item["operation"], item["message_bytes"]) for item in records
    ]
    duplicate_pairs = len(set(pairs)) != len(pairs)
    size_sets = {
        operation: {
            item["message_bytes"]
            for item in records
            if item["operation"] == operation
        }
        for operation in expected_operations
    }
    common_size_sweep = (
        len({tuple(sorted(values)) for values in size_sets.values()}) == 1
    )
    enough_sizes = args.fixture or all(
        len(values) >= 4 for values in size_sets.values()
    )
    passed = (
        bool(records)
        and all(item["correctness_passed"] for item in records)
        and world_sizes == {3}
        and operations == expected_operations
        and not duplicate_pairs
        and common_size_sweep
        and enough_sizes
    )
    document = {
        "schema_version": 1,
        "experiment_id": (
            "lesson-27-fixture" if args.fixture else "lesson-27-measured"
        ),
        "strategy": "network",
        "correctness": {"passed": passed},
        "environment": {
            "world_size": next(iter(world_sizes)) if len(world_sizes) == 1 else None,
            "fixture": args.fixture,
        },
        "measurements": {"records": records},
        "diagnostics": {
            "operations": sorted(operations),
            "sizes_by_operation": {
                key: sorted(value) for key, value in sorted(size_sets.items())
            },
            "duplicate_operation_size_pairs": duplicate_pairs,
            "common_size_sweep": common_size_sweep,
            "minimum_four_sizes_required": not args.fixture,
        },
        "limitations": [
            "payload rate is not measured NIC line rate",
            "all-reduce bus bandwidth is a reporting convention",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Network characterization report",
        "",
        f"- Fixture: `{args.fixture}`",
        f"- Correctness: `{passed}`",
        "",
        "| operation | bytes | median ms | payload Gbit/s |",
        "|---|---:|---:|---:|",
    ]
    for item in records:
        lines.append(
            f"| {item['operation']} | {item['message_bytes']} | "
            f"{item['median_seconds_slowest_rank'] * 1000:.3f} | "
            f"{item['payload_gbps']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Payload rate is not physical wire rate. Interpret with topology "
            "and NCCL transport logs.",
        ]
    )
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output} and {args.report}; passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
