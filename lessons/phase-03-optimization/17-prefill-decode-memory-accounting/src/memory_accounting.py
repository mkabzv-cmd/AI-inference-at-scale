#!/usr/bin/env python3
"""Explainable LLM-serving memory accounting.

This calculator intentionally reports a prediction, not a GPU measurement.  It
keeps every intermediate term so the learner can reconcile it with an engine's
startup logs and telemetry.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

GIB = 1024**3


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def gib(byte_count: float) -> float:
    return round(byte_count / GIB, 6)


def analyze(
    model: dict[str, Any],
    workloads: dict[str, Any],
    vram_gib: float,
    utilization: float,
    block_size: int,
) -> dict[str, Any]:
    if not 0 < utilization <= 1:
        raise ValueError("utilization must be in (0, 1]")
    if block_size <= 0:
        raise ValueError("block-size must be positive")

    parameter_count = int(model["parameter_count"])
    weight_bits = int(model["weight_bits"])
    quant_overhead = float(model["quantization_overhead_percent"]) / 100
    layers = int(model["num_hidden_layers"])
    kv_heads = int(model["num_key_value_heads"])
    head_dim = int(model["head_dim"])
    kv_bytes = int(model["kv_element_bytes"])

    raw_weight_bytes = parameter_count * weight_bits / 8
    stored_weight_bytes = raw_weight_bytes * (1 + quant_overhead)
    kv_payload_per_token = 2 * layers * kv_heads * head_dim * kv_bytes
    usable_bytes = vram_gib * GIB * utilization
    fixed_bytes = float(model["runtime_overhead_gib"]) * GIB
    workspace_bytes = float(model["workspace_gib"]) * GIB
    activation_per_token = int(model["activation_bytes_per_prefill_token"])

    scenarios = []
    for scenario in workloads["scenarios"]:
        concurrency = int(scenario["concurrency"])
        prompt_tokens = int(scenario["prompt_tokens"])
        output_tokens = int(scenario["max_output_tokens"])
        logical_tokens_per_sequence = prompt_tokens + output_tokens
        blocks_per_sequence = math.ceil(logical_tokens_per_sequence / block_size)
        allocated_tokens_per_sequence = blocks_per_sequence * block_size
        kv_payload_bytes = (
            concurrency * logical_tokens_per_sequence * kv_payload_per_token
        )
        kv_allocated_bytes = (
            concurrency * allocated_tokens_per_sequence * kv_payload_per_token
        )
        kv_internal_fragmentation_bytes = kv_allocated_bytes - kv_payload_bytes

        # This is a deliberately visible teaching approximation. Real peak
        # activation memory depends on kernels and scheduling/chunking.
        prefill_activation_bytes = (
            concurrency * prompt_tokens * activation_per_token
        )
        predicted_total = (
            stored_weight_bytes
            + fixed_bytes
            + workspace_bytes
            + kv_allocated_bytes
            + prefill_activation_bytes
        )
        scenarios.append(
            {
                "name": scenario["name"],
                "inputs": {
                    "concurrency": concurrency,
                    "prompt_tokens": prompt_tokens,
                    "max_output_tokens": output_tokens,
                },
                "kv": {
                    "payload_bytes_per_token": kv_payload_per_token,
                    "blocks_per_sequence": blocks_per_sequence,
                    "allocated_tokens_per_sequence": allocated_tokens_per_sequence,
                    "payload_gib": gib(kv_payload_bytes),
                    "allocated_gib": gib(kv_allocated_bytes),
                    "internal_fragmentation_mib": round(
                        kv_internal_fragmentation_bytes / 1024**2, 6
                    ),
                },
                "memory_gib": {
                    "weights": gib(stored_weight_bytes),
                    "runtime_fixed": gib(fixed_bytes),
                    "workspace": gib(workspace_bytes),
                    "prefill_activation_estimate": gib(
                        prefill_activation_bytes
                    ),
                    "kv_allocated": gib(kv_allocated_bytes),
                    "predicted_total": gib(predicted_total),
                    "usable_vram": gib(usable_bytes),
                    "predicted_headroom": gib(usable_bytes - predicted_total),
                },
                "predicted_fit": predicted_total <= usable_bytes,
                "compute_lower_bound": {
                    "prefill_model_flops_approx": (
                        2 * parameter_count * concurrency * prompt_tokens
                    ),
                    "decode_model_flops_approx": (
                        2 * parameter_count * concurrency * output_tokens
                    ),
                    "warning": (
                        "2*parameters*tokens omits attention-context work, "
                        "sampling, padding, and implementation overhead"
                    ),
                },
            }
        )

    return {
        "schema_version": "oms-optimization-memory/v1",
        "result_kind": "analytical_prediction_not_measurement",
        "model": {
            "id": model["model_id"],
            "revision": model["revision"],
            "parameter_count": parameter_count,
            "layers": layers,
            "attention_heads": int(model["num_attention_heads"]),
            "kv_heads": kv_heads,
            "head_dim": head_dim,
        },
        "assumptions": {
            "vram_gib": vram_gib,
            "engine_memory_utilization": utilization,
            "kv_block_size_tokens": block_size,
            "weight_bits": weight_bits,
            "kv_element_bytes": kv_bytes,
            "quantization_overhead_percent": (
                model["quantization_overhead_percent"]
            ),
            "activation_model": (
                "concurrency * prompt_tokens * configured activation bytes "
                "per token; assumes simultaneous prefill and is a teaching "
                "estimate only"
            ),
        },
        "constant_memory_gib": {
            "raw_weights": gib(raw_weight_bytes),
            "stored_weights": gib(stored_weight_bytes),
            "runtime_fixed": gib(fixed_bytes),
            "workspace": gib(workspace_bytes),
        },
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--vram-gib", type=float, default=24)
    parser.add_argument("--utilization", type=float, default=0.8)
    parser.add_argument("--block-size", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fail-on-infeasible",
        action="store_true",
        help="return 2 when any scenario exceeds the usable budget",
    )
    args = parser.parse_args()

    result = analyze(
        load_json(args.model),
        load_json(args.workloads),
        args.vram_gib,
        args.utilization,
        args.block_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for scenario in result["scenarios"]:
        memory = scenario["memory_gib"]
        print(
            f"{scenario['name']:<22} "
            f"total={memory['predicted_total']:>9.3f} GiB "
            f"headroom={memory['predicted_headroom']:>9.3f} GiB "
            f"fit={'yes' if scenario['predicted_fit'] else 'NO'}"
        )

    infeasible = [s["name"] for s in result["scenarios"] if not s["predicted_fit"]]
    if args.fail_on_infeasible and infeasible:
        print("infeasible scenarios: " + ", ".join(infeasible))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
