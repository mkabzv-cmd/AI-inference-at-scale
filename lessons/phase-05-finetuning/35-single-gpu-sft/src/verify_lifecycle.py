#!/usr/bin/env python3
"""Verify uninterrupted and checkpoint-resumed optimizer runs are equivalent."""

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_log(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--resumed", type=Path, required=True)
    args = parser.parse_args()

    full = load_json(args.full / "summary.json")
    resumed = load_json(args.resumed / "summary.json")
    full_log = load_log(args.full / "train-log.jsonl")
    resumed_log = load_log(args.resumed / "train-log.jsonl")

    assert full["complete"] and resumed["complete"]
    assert full["optimizer_step"] == resumed["optimizer_step"] == 12
    assert abs(full["final_weight"] - resumed["final_weight"]) < 1e-15
    assert abs(full["final_loss"] - resumed["final_loss"]) < 1e-15
    assert full_log == resumed_log
    assert full_log[-1]["full_dataset_loss"] < full_log[0]["full_dataset_loss"]
    assert any(row["gradient_was_clipped"] for row in full_log)
    assert all(
        row["microbatches_consumed"] == row["optimizer_step"] * 4
        for row in full_log
    )
    print(
        "PASS: resume exactly matches uninterrupted run; "
        f"loss {full_log[0]['full_dataset_loss']:.6f} "
        f"-> {full_log[-1]['full_dataset_loss']:.6f}"
    )


if __name__ == "__main__":
    main()
