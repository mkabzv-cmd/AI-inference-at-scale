#!/usr/bin/env python3
"""Estimate per-rank state memory and ring collective traffic."""

import argparse
import json
from pathlib import Path


def gib(value):
    return value / (1024**3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    world = int(config["world_size"])
    if world < 2:
        raise SystemExit("world_size must be at least two")
    if (
        float(config["model"]["parameters_billions"]) <= 0
        or float(config["model"]["largest_layer_parameters_millions"]) <= 0
        or float(config["per_rank_nonmodel_reserve_gib"]) < 0
        or any(float(value) <= 0 for value in config["bytes_per_parameter"].values())
    ):
        raise SystemExit("model sizes and byte assumptions must be positive")
    parameters = config["model"]["parameters_billions"] * 1_000_000_000
    largest_layer = (
        config["model"]["largest_layer_parameters_millions"] * 1_000_000
    )
    sizes = config["bytes_per_parameter"]
    parameter_bytes = parameters * sizes["bf16_parameter"]
    gradient_bytes = parameters * sizes["bf16_gradient"]
    optimizer_bytes = parameters * (
        sizes["fp32_master_parameter"] + sizes["fp32_adam_moments"]
    )
    full_state = parameter_bytes + gradient_bytes + optimizer_bytes
    ring_factor = 2 * (world - 1) / world

    estimates = {
        "ddp": {
            "state_gib_per_rank": gib(full_state),
            "largest_layer_all_gather_gib": 0.0,
            "gradient_all_reduce_gib_per_rank": gib(
                ring_factor * gradient_bytes
            ),
            "fits_by_state_arithmetic_only": False
        },
        "zero-1": {
            "state_gib_per_rank": gib(
                parameter_bytes + gradient_bytes + optimizer_bytes / world
            ),
            "largest_layer_all_gather_gib": 0.0
        },
        "zero-2": {
            "state_gib_per_rank": gib(
                parameter_bytes
                + (gradient_bytes + optimizer_bytes) / world
            ),
            "largest_layer_all_gather_gib": 0.0
        },
        "zero-3": {
            "state_gib_per_rank": gib(full_state / world),
            "largest_layer_all_gather_gib": gib(
                largest_layer * sizes["bf16_parameter"]
            )
        },
        "fsdp2-full-shard": {
            "state_gib_per_rank": gib(full_state / world),
            "largest_layer_all_gather_gib": gib(
                largest_layer * sizes["bf16_parameter"]
            )
        }
    }
    for value in estimates.values():
        value["planning_gib_with_nonmodel_reserve"] = (
            value["state_gib_per_rank"]
            + value["largest_layer_all_gather_gib"]
            + config["per_rank_nonmodel_reserve_gib"]
        )
    report = {
        "schema_version": 1,
        "world_size": world,
        "model_parameters": int(parameters),
        "replication_rule": (
            "DDP keeps a full parameter, gradient, and optimizer-state "
            "replica on every rank; it does not pool model memory."
        ),
        "ring_factor_approximation": ring_factor,
        "collective_payload_estimates": {
            "ddp_gradient_ring_all_reduce_gib_per_rank": gib(
                ring_factor * gradient_bytes
            ),
            "one_full_parameter_all_gather_gib_per_rank": gib(
                (world - 1) / world * parameter_bytes
            ),
            "one_full_gradient_reduce_scatter_gib_per_rank": gib(
                (world - 1) / world * gradient_bytes
            ),
            "warning": (
                "FSDP2/ZeRO can materialize and reshard more than once per "
                "training step; these are one-collective payload estimates."
            ),
        },
        "estimates": estimates,
        "warning": config["warning"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("PASS: wrote replication and sharding memory/traffic estimates")


if __name__ == "__main__":
    main()
