#!/usr/bin/env python3
"""Verify the authored scenarios exercise four distinct recommendations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.results.read_text(encoding="utf-8"))
    failures = []
    recommendations = set()
    for result in document["results"]:
        recommendations.add(result["recommendation"])
        if result["recommendation"] != result["expected_recommendation"]:
            failures.append(
                f"{result['id']}: expected {result['expected_recommendation']}, "
                f"got {result['recommendation']}"
            )
        selected = next(
            item
            for item in result["rankings"]
            if item["strategy"] == result["recommendation"]
        )
        if not selected["feasible"]:
            failures.append(f"{result['id']}: selected strategy is infeasible")
    if len(recommendations) != 4:
        failures.append("fixtures should exercise four different outcomes")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS: hard constraints and weighted assumptions produce the four "
        "reviewed scenario recommendations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
