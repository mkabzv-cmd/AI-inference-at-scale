#!/usr/bin/env python3
"""Conservative training memory/disk arithmetic; not a CUDA measurement."""

import argparse
import json


def gib(byte_count: float) -> float:
    return byte_count / (1024**3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters-billions", type=float, default=0.494)
    parser.add_argument("--sequence-length", type=int, default=512)
    parser.add_argument("--microbatch", type=int, default=1)
    parser.add_argument("--hidden-size", type=int, default=896)
    parser.add_argument("--layers", type=int, default=24)
    parser.add_argument("--activation-multiplier", type=float, default=12.0)
    args = parser.parse_args()
    if (
        args.parameters_billions <= 0
        or args.sequence_length < 1
        or args.microbatch < 1
        or args.hidden_size < 1
        or args.layers < 1
        or args.activation_multiplier <= 0
    ):
        raise SystemExit("all model, batch, sequence, and activation inputs must be positive")

    parameters = args.parameters_billions * 1_000_000_000
    weights = parameters * 2
    gradients = parameters * 2
    master_weights = parameters * 4
    adam_moments = parameters * 8
    activations = (
        args.microbatch
        * args.sequence_length
        * args.hidden_size
        * args.layers
        * args.activation_multiplier
        * 2
    )
    raw = weights + gradients + master_weights + adam_moments + activations
    result = {
        "schema_version": 1,
        "warning": "planning estimate only; measure allocated and reserved CUDA memory",
        "assumptions": {
            "parameters_billions": args.parameters_billions,
            "weight_and_gradient_bytes": 2,
            "master_weight_bytes": 4,
            "adam_moment_bytes": 8,
            "activation_multiplier": args.activation_multiplier,
        },
        "gib": {
            "weights": gib(weights),
            "gradients": gib(gradients),
            "master_weights": gib(master_weights),
            "adam_moments": gib(adam_moments),
            "activation_estimate": gib(activations),
            "raw_total_before_allocator_and_kernels": gib(raw),
            "planning_total_with_25_percent_headroom": gib(raw * 1.25),
            "one_full_checkpoint_approximation": gib(weights),
            "checkpoint_plus_optimizer_approximation": gib(
                weights + master_weights + adam_moments
            ),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
