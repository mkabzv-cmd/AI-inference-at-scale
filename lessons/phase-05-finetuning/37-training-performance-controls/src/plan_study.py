#!/usr/bin/env python3
"""Turn training controls into comparable optimizer-step arithmetic."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    candidates = []
    reference_slots = None
    for row in config["candidates"]:
        microbatch = int(row["microbatch_size"])
        accumulation = int(row["gradient_accumulation_steps"])
        sequence = int(row["sequence_length"])
        if microbatch < 1 or accumulation < 1 or sequence < 1:
            raise SystemExit(
                "microbatch, accumulation, and sequence length must be positive"
            )
        slots = microbatch * accumulation * sequence
        if reference_slots is None:
            reference_slots = slots
        comparable = slots == reference_slots
        candidates.append(
            {
                **row,
                "sequences_per_optimizer_step": microbatch * accumulation,
                "token_slots_per_optimizer_step": slots,
                "optimizer_updates": config["frozen_invariants"][
                    "maximum_optimizer_steps"
                ],
                "strictly_comparable_slot_budget": comparable,
                "measurement_required_for_nonpadding_tokens": True,
            }
        )
    if not all(row["strictly_comparable_slot_budget"] for row in candidates):
        raise SystemExit(
            "candidate changes token slots per optimizer update; "
            "place it in a separately named optimization study"
        )
    frozen_invariants = dict(config["frozen_invariants"])
    frozen_invariants["dataset_manifest_sha256"] = hashlib.sha256(
        args.dataset_manifest.read_bytes()
    ).hexdigest()
    report = {
        "schema_version": 1,
        "study": config["study"],
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "frozen_invariants": frozen_invariants,
        "candidates": candidates,
        "measurement_policy": {
            "warmup_optimizer_steps_excluded": 10,
            "minimum_measured_optimizer_steps": 30,
            "throughput_numerator": "nonpadding supervised and context tokens",
            "memory_metric": "CUDA peak allocated and peak reserved bytes",
            "quality_metric": "frozen validation and acceptance contracts",
            "claim_policy": "fixture outputs are not hardware results"
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"PASS: {len(candidates)} candidates preserve "
        f"{reference_slots} token slots per optimizer step"
    )


if __name__ == "__main__":
    main()
