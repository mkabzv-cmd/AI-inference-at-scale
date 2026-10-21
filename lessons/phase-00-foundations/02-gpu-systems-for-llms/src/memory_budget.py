#!/usr/bin/env python3
"""Estimate model-weight and KV-cache memory before allocating a model."""

import argparse
import json
from pathlib import Path

GIB = 1024 ** 3


def non_negative(value):
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


parser = argparse.ArgumentParser()
parser.add_argument("--label", default="memory-plan")
parser.add_argument("--params-billion", required=True, type=non_negative)
parser.add_argument("--weight-bits", required=True, type=non_negative)
parser.add_argument("--quant-overhead-percent", default=0, type=non_negative)
parser.add_argument("--layers", default=0, type=int)
parser.add_argument("--kv-heads", default=0, type=int)
parser.add_argument("--head-dim", default=0, type=int)
parser.add_argument("--sequences", default=0, type=int)
parser.add_argument("--tokens-per-sequence", default=0, type=int)
parser.add_argument("--kv-bits", default=16, type=non_negative)
parser.add_argument("--vram-gib", required=True, type=non_negative)
parser.add_argument("--reserve-percent", default=10, type=non_negative)
parser.add_argument("--output", type=Path)
args = parser.parse_args()

integer_fields = {
    "layers": args.layers,
    "kv-heads": args.kv_heads,
    "head-dim": args.head_dim,
    "sequences": args.sequences,
    "tokens-per-sequence": args.tokens_per_sequence,
}
for name, value in integer_fields.items():
    if value < 0:
        parser.error(f"--{name} must be non-negative")
if args.weight_bits <= 0 or args.kv_bits <= 0:
    parser.error("bit widths must be greater than zero")
if args.reserve_percent >= 100:
    parser.error("--reserve-percent must be less than 100")

parameters = args.params_billion * 1_000_000_000
raw_weight_bytes = parameters * args.weight_bits / 8
quant_overhead_bytes = raw_weight_bytes * args.quant_overhead_percent / 100
kv_bytes = (
    2
    * args.layers
    * args.sequences
    * args.tokens_per_sequence
    * args.kv_heads
    * args.head_dim
    * args.kv_bits
    / 8
)
subtotal_bytes = raw_weight_bytes + quant_overhead_bytes + kv_bytes
usable_bytes = args.vram_gib * GIB * (1 - args.reserve_percent / 100)
headroom_bytes = usable_bytes - subtotal_bytes
fits = headroom_bytes >= 0

result = {
    "schema_version": 1,
    "label": args.label,
    "inputs": vars(args).copy(),
    "memory_gib": {
        "raw_weights": raw_weight_bytes / GIB,
        "quantization_overhead": quant_overhead_bytes / GIB,
        "kv_cache": kv_bytes / GIB,
        "estimated_subtotal": subtotal_bytes / GIB,
        "usable_after_reserve": usable_bytes / GIB,
        "headroom_before_other_overhead": headroom_bytes / GIB,
    },
    "fits_simplified_budget": fits,
}
result["inputs"]["output"] = str(args.output) if args.output else None

print(f"raw weight memory:         {raw_weight_bytes / GIB:8.3f} GiB")
print(f"quantization overhead:     {quant_overhead_bytes / GIB:8.3f} GiB")
print(f"estimated KV cache:        {kv_bytes / GIB:8.3f} GiB")
print(f"estimated subtotal:        {subtotal_bytes / GIB:8.3f} GiB")
print(f"usable VRAM after reserve: {usable_bytes / GIB:8.3f} GiB")
print(f"headroom before overhead:  {headroom_bytes / GIB:8.3f} GiB")
print(f"fit prediction: {'YES' if fits else 'NO'}")

if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"result written to {args.output}")

raise SystemExit(0 if fits else 3)
