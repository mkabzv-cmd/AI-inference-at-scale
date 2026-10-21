#!/usr/bin/env python3
"""Validate targets and calculate LoRA parameter/storage arithmetic."""

import argparse
import json
from pathlib import Path


def dimensions(model):
    hidden = int(model["hidden_size"])
    intermediate = int(model["intermediate_size"])
    kv = int(model["key_value_heads"]) * int(model["head_dimension"])
    return {
        "q_proj": (hidden, hidden),
        "k_proj": (hidden, kv),
        "v_proj": (hidden, kv),
        "o_proj": (hidden, hidden),
        "gate_proj": (hidden, intermediate),
        "up_proj": (hidden, intermediate),
        "down_proj": (intermediate, hidden),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--available", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    available = set(json.loads(args.available.read_text())["modules"])
    dims = dimensions(config["model"])
    layers = int(config["model"]["layers"])
    rows = []
    failures = []
    for candidate in config["candidates"]:
        rank = int(candidate["rank"])
        alpha = float(candidate["alpha"])
        if rank < 1 or alpha <= 0:
            failures.append(
                f"{candidate['name']}: rank and alpha must be positive"
            )
        if candidate["method"] not in {"lora", "qlora-nf4"}:
            failures.append(
                f"{candidate['name']}: unsupported method "
                f"{candidate['method']!r}"
            )
        missing = sorted(set(candidate["targets"]) - available)
        missing_dimensions = sorted(set(candidate["targets"]) - set(dims))
        if missing:
            failures.append(
                f"{candidate['name']}: target modules not found: {', '.join(missing)}"
            )
        if missing_dimensions:
            failures.append(
                f"{candidate['name']}: target dimensions are unknown: "
                f"{', '.join(missing_dimensions)}"
            )
        if (
            candidate["method"] == "qlora-nf4"
            and candidate["merge_policy"] != "reload-nonquantized-base-then-merge"
        ):
            failures.append(
                f"{candidate['name']}: NF4 adapter merge must reload a "
                "nonquantized base before merge"
            )
        trainable = sum(
            rank * (dims[name][0] + dims[name][1])
            for name in candidate["targets"]
            if name in dims
        ) * layers
        rows.append(
            {
                "name": candidate["name"],
                "method": candidate["method"],
                "rank": rank,
                "alpha": candidate["alpha"],
                "scale": candidate["alpha"] / rank,
                "targets": candidate["targets"],
                "trainable_parameters": trainable,
                "adapter_weight_bytes_bf16": trainable * 2,
                "adam_state_bytes_fp32_moments": trainable * 8,
                "parameter_count_is_architecture_arithmetic_not_measurement": True,
            }
        )
    if failures:
        raise SystemExit("; ".join(failures))
    report = {
        "schema_version": 1,
        "model": config["model"],
        "candidates": rows,
        "warning": (
            "Storage arithmetic excludes metadata, allocator overhead, "
            "activations, temporary buffers, and quantization scales."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS: planned {len(rows)} valid adapter candidates")


if __name__ == "__main__":
    main()
