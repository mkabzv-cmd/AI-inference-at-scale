#!/usr/bin/env python3
"""Validate and estimate a simple DP/TP/PP inference layout."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


GIB = 1024**3


def pipeline_ranges(layers: int, stages: int) -> list[list[int]]:
    if layers < 1 or stages < 1:
        raise ValueError("layers and stages must be positive")
    quotient, remainder = divmod(layers, stages)
    counts = [
        quotient + (1 if stage < remainder else 0)
        for stage in range(stages)
    ]
    ranges = []
    start = 0
    for count in counts:
        end = start + count - 1
        ranges.append([start, end] if count else [])
        start += count
    return ranges


def evaluate(
    model_name: str,
    model: dict[str, Any],
    *,
    gpus: int,
    dp: int,
    tp: int,
    pp: int,
) -> dict[str, Any]:
    reasons = []
    warnings = []
    for name, value in (("gpus", gpus), ("dp", dp), ("tp", tp), ("pp", pp)):
        if value < 1:
            reasons.append(f"{name} must be positive")

    world_size = dp * tp * pp if dp > 0 and tp > 0 and pp > 0 else None
    if reasons:
        return {
            "schema_version": 1,
            "model": model_name,
            "valid": False,
            "reasons": reasons,
            "warnings": [
                "arithmetic estimates are omitted until all factors are positive"
            ],
            "layout": {
                "gpus": gpus,
                "dp": dp,
                "tp": tp,
                "pp": pp,
                "world_size": world_size,
                "pipeline_layers": [],
                "pipeline_layer_counts": [],
            },
            "checks": {},
            "memory": {
                "estimated_total_gib_per_rank": None,
                "usable_vram_gib_per_rank": None,
                "fits_estimate": False,
            },
            "communication_estimate": {
                "tp_collective_payload_bytes_per_token_per_rank": None,
                "pp_boundary_payload_bytes_per_token": None,
                "activation_message_bytes": None,
                "warning": "invalid factors prevent arithmetic",
            },
        }

    assert world_size is not None
    if world_size != gpus:
        reasons.append(
            f"DP*TP*PP={world_size}, but gpus={gpus}; every rank needs a role"
        )

    hidden = int(model["hidden_size"])
    attention_heads = int(model["attention_heads"])
    kv_heads = int(model["kv_heads"])
    layers = int(model["layers"])
    vocab = int(model["vocab_size"])
    if hidden % attention_heads:
        reasons.append("hidden_size must divide evenly by attention_heads")
        head_dim = None
    else:
        head_dim = hidden // attention_heads

    if hidden % tp:
        reasons.append(f"hidden_size={hidden} is not divisible by TP={tp}")
    if attention_heads % tp:
        reasons.append(
            f"attention_heads={attention_heads} is not divisible by TP={tp}"
        )
    if kv_heads % tp and not bool(model["allow_kv_head_replication"]):
        reasons.append(f"kv_heads={kv_heads} is not divisible by TP={tp}")
    elif kv_heads % tp:
        warnings.append("KV heads require engine-supported replication")
    if layers < pp:
        reasons.append(f"layers={layers} cannot give work to PP={pp} stages")

    ranges = pipeline_ranges(layers, pp)
    counts = [
        item[1] - item[0] + 1 if item else 0
        for item in ranges
    ]
    if counts and max(counts) != min(counts):
        warnings.append(f"pipeline layer counts are uneven: {counts}")

    padded_vocab = math.ceil(vocab / tp) * tp
    if padded_vocab != vocab:
        warnings.append(
            f"vocabulary requires padding from {vocab} to {padded_vocab}"
        )

    raw_weight_bytes = (
        float(model["parameters_billion"])
        * 1_000_000_000
        * float(model["bytes_per_weight"])
    )
    model_parallel = tp * pp
    average_weight_per_rank = raw_weight_bytes / model_parallel
    layer_balance_factor = (
        max(counts) / (layers / pp) if counts and layers > 0 else 1.0
    )
    screening_weight_per_rank = (
        average_weight_per_rank * layer_balance_factor
    )
    kv_total = 0.0
    average_kv_per_rank = 0.0
    screening_kv_per_rank = 0.0
    local_kv_heads = None
    if head_dim is not None:
        kv_total = (
            2
            * layers
            * int(model["concurrent_sequences"])
            * int(model["sequence_tokens"])
            * kv_heads
            * head_dim
            * int(model["kv_element_bytes"])
        )
        average_kv_per_rank = kv_total / model_parallel
        local_kv_heads = math.ceil(kv_heads / tp)
        screening_kv_per_rank = (
            2
            * max(counts)
            * int(model["concurrent_sequences"])
            * int(model["sequence_tokens"])
            * local_kv_heads
            * head_dim
            * int(model["kv_element_bytes"])
        )
    overhead = float(model["runtime_overhead_gib"]) * GIB
    estimated_total = (
        screening_weight_per_rank + screening_kv_per_rank + overhead
    )
    usable = (
        float(model["gpu_vram_gib"])
        * GIB
        * (1.0 - float(model["reserve_fraction"]))
    )
    fits = estimated_total <= usable
    if not fits:
        reasons.append(
            "estimated weights + KV cache + explicit runtime overhead exceed "
            "the reserved VRAM budget"
        )

    local_layers = max(counts)
    activation_message = (
        hidden
        * int(model["activation_bytes"])
        * int(model["concurrent_sequences"])
    )
    ring_factor = 0.0 if tp == 1 else 2 * (tp - 1) / tp
    tp_bytes_per_token = (
        2 * local_layers * ring_factor * activation_message
    )
    pp_bytes_per_token = (pp - 1) * activation_message

    return {
        "schema_version": 1,
        "model": model_name,
        "valid": not reasons,
        "reasons": reasons,
        "warnings": warnings,
        "layout": {
            "gpus": gpus,
            "dp": dp,
            "tp": tp,
            "pp": pp,
            "world_size": world_size,
            "pipeline_layers": ranges,
            "pipeline_layer_counts": counts,
        },
        "checks": {
            "hidden_size": hidden,
            "attention_heads": attention_heads,
            "kv_heads": kv_heads,
            "head_dim": head_dim,
            "padded_vocab_size": padded_vocab,
        },
        "memory": {
            "raw_weight_gib_total": raw_weight_bytes / GIB,
            "average_weight_gib_per_rank": average_weight_per_rank / GIB,
            "pipeline_layer_imbalance_factor": layer_balance_factor,
            "weight_gib_per_rank": screening_weight_per_rank / GIB,
            "kv_cache_gib_total_per_replica": kv_total / GIB,
            "average_kv_cache_gib_per_rank": average_kv_per_rank / GIB,
            "kv_cache_gib_per_rank": screening_kv_per_rank / GIB,
            "screening_local_layers": local_layers,
            "screening_local_kv_heads": local_kv_heads,
            "runtime_overhead_gib_per_rank": overhead / GIB,
            "estimated_total_gib_per_rank": estimated_total / GIB,
            "usable_vram_gib_per_rank": usable / GIB,
            "fits_estimate": fits,
        },
        "communication_estimate": {
            "tp_collective_payload_bytes_per_token_per_rank": tp_bytes_per_token,
            "pp_boundary_payload_bytes_per_token": pp_bytes_per_token,
            "activation_message_bytes": activation_message,
            "warning": (
                "algorithmic comparison only; not physical network bytes "
                "or an engine trace"
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--gpus", type=int, required=True)
    parser.add_argument("--dp", type=int, required=True)
    parser.add_argument("--tp", type=int, required=True)
    parser.add_argument("--pp", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models = json.loads(args.models.read_text(encoding="utf-8"))
    if args.model not in models:
        raise SystemExit(
            f"unknown model {args.model!r}; choose one of {sorted(models)}"
        )
    result = evaluate(
        args.model,
        models[args.model],
        gpus=args.gpus,
        dp=args.dp,
        tp=args.tp,
        pp=args.pp,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            result,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"model={args.model} valid={result['valid']} "
        f"output={args.output}"
    )
    for reason in result["reasons"]:
        print(f"REJECT: {reason}")
    for warning in result["warnings"]:
        print(f"WARN: {warning}")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
