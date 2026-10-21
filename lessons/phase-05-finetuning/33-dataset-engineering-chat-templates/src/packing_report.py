#!/usr/bin/env python3
"""Compare padding-every-example with greedy sequence packing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.max_length < 1:
        parser.error("--max-length must be positive")

    lengths = []
    for split in ("train", "validation", "test"):
        path = args.dataset_dir / f"{split}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                length = int(row["token_count"])
                if length > args.max_length:
                    raise SystemExit(
                        f"{row['id']} length {length} exceeds max length "
                        f"{args.max_length}"
                    )
                lengths.append(length)

    padded_slots = len(lengths) * args.max_length
    used_slots = sum(lengths)

    bins: list[int] = []
    for length in sorted(lengths, reverse=True):
        for index, used in enumerate(bins):
            if used + length <= args.max_length:
                bins[index] += length
                break
        else:
            bins.append(length)

    packed_slots = len(bins) * args.max_length
    payload = {
        "schema_version": 1,
        "max_length": args.max_length,
        "examples": len(lengths),
        "tokens": used_slots,
        "pad_each_example": {
            "allocated_slots": padded_slots,
            "wasted_slots": padded_slots - used_slots,
            "utilization": used_slots / padded_slots,
        },
        "greedy_pack": {
            "sequences": len(bins),
            "used_per_sequence": bins,
            "allocated_slots": packed_slots,
            "wasted_slots": packed_slots - used_slots,
            "utilization": used_slots / packed_slots,
        },
        "warning": (
            "Packing changes attention boundaries unless the collator/model "
            "prevents examples from attending across packed samples."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"pad utilization={payload['pad_each_example']['utilization']:.3f}; "
        f"pack utilization={payload['greedy_pack']['utilization']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
