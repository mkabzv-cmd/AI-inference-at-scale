#!/usr/bin/env python3
"""Verify that the checked-in fixture exercises both pass and fail paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    args = parser.parse_args()

    results = json.loads(args.results.read_text(encoding="utf-8"))
    decision = json.loads(args.decision.read_text(encoding="utf-8"))
    failures = []
    if results["examples"] != 8:
        failures.append("expected eight frozen acceptance examples")
    if not (0 < results["passed"] < results["examples"]):
        failures.append("fixture must contain both passing and failing examples")
    if results["forbidden_hits"] < 1:
        failures.append("fixture must exercise forbidden-claim detection")
    if decision["release"]:
        failures.append("the intentionally weak base fixture must fail release")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS: frozen baseline produced mixed item results and correctly "
        "failed the predeclared release gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
