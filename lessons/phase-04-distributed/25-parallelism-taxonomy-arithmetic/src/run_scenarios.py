#!/usr/bin/env python3
"""Evaluate a declared scenario matrix and verify expected validity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from layout_planner import evaluate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    models = json.loads(args.models.read_text(encoding="utf-8"))
    scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    results = []
    for scenario in scenarios:
        result = evaluate(
            scenario["model"],
            models[scenario["model"]],
            gpus=scenario["gpus"],
            dp=scenario["dp"],
            tp=scenario["tp"],
            pp=scenario["pp"],
        )
        result["name"] = scenario["name"]
        result["expected_valid"] = scenario["expected_valid"]
        result["expectation_matched"] = (
            result["valid"] == scenario["expected_valid"]
        )
        results.append(result)

    passed = all(item["expectation_matched"] for item in results)
    document = {
        "schema_version": 1,
        "experiment_id": "lesson-25-scenario-matrix",
        "strategy": "capstone",
        "correctness": {"passed": passed},
        "environment": {"python_only": True},
        "measurements": {
            "scenario_count": len(results),
            "valid_count": sum(item["valid"] for item in results),
        },
        "scenarios": results,
        "limitations": [
            "memory and communication values are planning estimates"
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            document,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; expectations_passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
