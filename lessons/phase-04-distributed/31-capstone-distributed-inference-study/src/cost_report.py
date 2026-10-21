#!/usr/bin/env python3
"""Calculate GPU-hours and node cost from the full capacity window."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument("--gpus-per-node", type=int, required=True)
    parser.add_argument("--price-per-node-hour", type=float, required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = parse_timestamp(args.start)
    end = parse_timestamp(args.end)
    seconds = (end - start).total_seconds()
    if (
        seconds <= 0
        or args.nodes < 1
        or args.gpus_per_node < 1
        or args.price_per_node_hour <= 0
    ):
        raise SystemExit("timestamps/order/counts/price are invalid")
    hours = seconds / 3600
    document = {
        "capacity_start": args.start,
        "capacity_end": args.end,
        "capacity_window_seconds": seconds,
        "node_count": args.nodes,
        "gpus_per_node": args.gpus_per_node,
        "gpu_hours": hours * args.nodes * args.gpus_per_node,
        "price_per_node_hour": args.price_per_node_hour,
        "estimated_node_cost": hours
        * args.nodes
        * args.price_per_node_hour,
        "currency": args.currency,
        "excluded": [
            "EKS control plane",
            "storage and data transfer",
            "discounts, commitments, taxes, and billing granularity",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; gpu_hours={document['gpu_hours']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
