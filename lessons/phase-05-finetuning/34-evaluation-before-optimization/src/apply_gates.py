#!/usr/bin/env python3
"""Apply a predeclared release gate without changing the acceptance set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--gates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit nonzero when the release decision is fail.",
    )
    args = parser.parse_args()

    results = json.loads(args.results.read_text(encoding="utf-8"))
    gates = json.loads(args.gates.read_text(encoding="utf-8"))
    checks = []

    checks.append(
        {
            "name": "minimum_overall_pass_rate",
            "observed": results["overall_pass_rate"],
            "required": gates["minimum_overall_pass_rate"],
            "pass": (
                results["overall_pass_rate"]
                >= gates["minimum_overall_pass_rate"]
            ),
        }
    )
    checks.append(
        {
            "name": "maximum_forbidden_hits",
            "observed": results["forbidden_hits"],
            "required": gates["maximum_forbidden_hits"],
            "pass": (
                results["forbidden_hits"]
                <= gates["maximum_forbidden_hits"]
            ),
        }
    )
    checks.append(
        {
            "name": "minimum_answered_examples",
            "observed": results["examples"],
            "required": gates["minimum_answered_examples"],
            "pass": results["examples"] >= gates["minimum_answered_examples"],
        }
    )
    for slice_name, minimum in gates["minimum_slice_pass_rate"].items():
        observed = results["slices"].get(slice_name, {}).get("pass_rate", 0.0)
        checks.append(
            {
                "name": f"slice:{slice_name}",
                "observed": observed,
                "required": minimum,
                "pass": observed >= minimum,
            }
        )

    passed = all(check["pass"] for check in checks)
    payload = {
        "schema_version": 1,
        "release": passed,
        "decision": "pass" if passed else "fail",
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"release_decision={payload['decision']}")
    if args.require_pass and not passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
