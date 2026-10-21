#!/usr/bin/env python3
"""Verify the CPU lab's behavioral claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    memory = json.loads(args.memory.read_text(encoding="utf-8"))

    problems: list[str] = []
    if trace.get("schema_version") != 1:
        problems.append("training trace schema_version is not 1")
    if trace["final_loss"] >= trace["initial_loss"] * 0.5:
        problems.append("loss did not fall by at least 50 percent")

    inventory = trace["graph_inventory"]
    parameter_elements = inventory["parameter_elements"]
    if inventory["gradient_elements"] != parameter_elements:
        problems.append("the full-training gradient inventory is incomplete")
    if inventory["optimizer_state_elements"] != 2 * parameter_elements:
        problems.append("Adam first/second-moment inventory is incomplete")

    cases = {case["name"]: case for case in memory["cases"]}
    required_cases = {
        "inference-bf16",
        "full-training-adamw-mixed-precision",
        "full-training-checkpointed-activations",
    }
    if set(cases) != required_cases:
        problems.append("memory output is missing or adds an unexpected case")
    else:
        inference = cases["inference-bf16"]["total_bytes"]
        training = cases["full-training-adamw-mixed-precision"]["total_bytes"]
        checkpointed = cases[
            "full-training-checkpointed-activations"
        ]["total_bytes"]
        if not (training > checkpointed > inference):
            problems.append(
                "expected full training > checkpointed training > inference"
            )

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    print(
        "PASS: loss decreased; gradients and Adam states exist; "
        "training memory exceeds inference; checkpointing lowers retained "
        "activation memory in the planning cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
