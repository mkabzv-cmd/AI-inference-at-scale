#!/usr/bin/env python3
"""Calculate planned node-hours and GPU-hours without a cloud API."""

import argparse


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


parser = argparse.ArgumentParser()
parser.add_argument("--nodes", required=True, type=non_negative_int)
parser.add_argument("--gpus-per-node", required=True, type=non_negative_int)
parser.add_argument("--minutes", required=True, type=non_negative_float)
parser.add_argument("--hourly-node-price", type=non_negative_float)
args = parser.parse_args()

node_hours = args.nodes * args.minutes / 60
gpu_hours = args.nodes * args.gpus_per_node * args.minutes / 60
print(f"nodes:             {args.nodes}")
print(f"GPUs per node:     {args.gpus_per_node}")
print(f"planned minutes:   {args.minutes:.2f}")
print(f"node-hours:        {node_hours:.4f}")
print(f"GPU-hours:         {gpu_hours:.4f}")
if args.hourly_node_price is None:
    print(
        "currency estimate: omitted "
        "(pass --hourly-node-price with a current regional price)"
    )
else:
    print(f"compute estimate:  {node_hours * args.hourly_node_price:.4f}")
    print("estimate excludes storage, networking, load balancers, and taxes")
