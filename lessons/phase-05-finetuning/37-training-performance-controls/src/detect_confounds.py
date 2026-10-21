#!/usr/bin/env python3
"""Fail when a performance result changes frozen experiment invariants."""

import argparse
import json
from pathlib import Path


KEYS = (
    "model_revision",
    "dataset_manifest_sha256",
    "maximum_optimizer_steps",
    "token_slots_per_optimizer_step",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    expected = source["invariants"]
    failures = []
    for row in source["runs"]:
        for key in KEYS:
            observed = row.get(key, expected.get(key))
            if observed != expected[key]:
                failures.append(
                    f"{row['name']}: {key}={observed!r}, "
                    f"expected {expected[key]!r}"
                )
    if failures:
        raise SystemExit("confounded comparison: " + "; ".join(failures))
    print(f"PASS: {len(source['runs'])} runs preserve frozen invariants")


if __name__ == "__main__":
    main()
