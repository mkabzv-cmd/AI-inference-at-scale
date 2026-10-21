#!/usr/bin/env python3
"""Dependency-free optimizer lifecycle used to test checkpoint/resume mechanics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def learning_rate(config: dict, step: int) -> float:
    peak = float(config["learning_rate"])
    warmup = int(config["warmup_steps"])
    maximum = int(config["maximum_optimizer_steps"])
    if step <= warmup:
        return peak * step / max(1, warmup)
    remaining = max(0, maximum - step)
    return peak * remaining / max(1, maximum - warmup)


def mean_loss(weight: float, examples: list[dict]) -> float:
    return sum(
        0.5 * (weight * float(row["x"]) - float(row["y"])) ** 2
        for row in examples
    ) / len(examples)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_state(path: Path, expected_hash: str) -> dict:
    state = json.loads(path.read_text())
    if state["config_sha256"] != expected_hash:
        raise SystemExit(
            "checkpoint configuration mismatch: refusing an inexact resume"
        )
    return state


def run(
    config_path: Path,
    output: Path,
    resume: Path | None,
    stop_after: int | None,
) -> None:
    config = json.loads(config_path.read_text())
    config_hash = canonical_hash(config)
    examples = config["examples"]
    accumulation = int(config["gradient_accumulation_steps"])
    maximum_steps = int(config["maximum_optimizer_steps"])
    if not examples or accumulation < 1 or maximum_steps < 1:
        raise SystemExit("examples and step counts must be positive")

    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "train-log.jsonl"
    if resume:
        state = load_state(resume, config_hash)
        weight = float(state["weight"])
        cursor = int(state["example_cursor"])
        optimizer_step = int(state["optimizer_step"])
        log_mode = "a"
    else:
        weight = float(config["initial_weight"])
        cursor = 0
        optimizer_step = 0
        log_mode = "w"

    initial_loss = mean_loss(weight, examples)
    with log_path.open(log_mode) as log_file:
        while optimizer_step < maximum_steps:
            raw_gradient = 0.0
            micro_losses = []
            for _ in range(accumulation):
                row = examples[cursor % len(examples)]
                x_value = float(row["x"])
                target = float(row["y"])
                error = weight * x_value - target
                micro_losses.append(0.5 * error * error)
                raw_gradient += error * x_value
                cursor += 1

            raw_gradient /= accumulation
            maximum_norm = float(config["maximum_gradient_norm"])
            clipped_gradient = max(
                -maximum_norm, min(maximum_norm, raw_gradient)
            )
            optimizer_step += 1
            rate = learning_rate(config, optimizer_step)
            weight -= rate * clipped_gradient
            record = {
                "schema_version": 1,
                "optimizer_step": optimizer_step,
                "microbatches_consumed": cursor,
                "mean_microbatch_loss": sum(micro_losses)
                / len(micro_losses),
                "full_dataset_loss": mean_loss(weight, examples),
                "learning_rate": rate,
                "raw_gradient_norm": abs(raw_gradient),
                "clipped_gradient_norm": abs(clipped_gradient),
                "gradient_was_clipped": abs(raw_gradient) > maximum_norm,
                "weight": weight,
            }
            log_file.write(json.dumps(record, sort_keys=True) + "\n")
            log_file.flush()

            state = {
                "schema_version": 1,
                "config_sha256": config_hash,
                "optimizer_step": optimizer_step,
                "example_cursor": cursor,
                "weight": weight,
            }
            checkpoint = output / f"checkpoint-{optimizer_step:04d}.json"
            write_json(checkpoint, state)
            write_json(output / "last-checkpoint.json", state)

            if stop_after is not None and optimizer_step >= stop_after:
                break

    summary = {
        "schema_version": 1,
        "experiment": config["experiment"],
        "config_sha256": config_hash,
        "initial_loss_for_this_invocation": initial_loss,
        "final_loss": mean_loss(weight, examples),
        "final_weight": weight,
        "optimizer_step": optimizer_step,
        "microbatches_consumed": cursor,
        "complete": optimizer_step == maximum_steps,
        "finite": math.isfinite(weight),
    }
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--stop-after", type=int)
    args = parser.parse_args()
    run(args.config, args.output, args.resume, args.stop_after)


if __name__ == "__main__":
    main()
