#!/usr/bin/env python3
"""Deterministic two-layer tensor-parallel toy model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("gloo", "nccl"), default="gloo")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--input-size", type=int, default=6)
    parser.add_argument("--hidden-size", type=int, default=12)
    parser.add_argument("--output-size", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/local/summary.json")
    )
    return parser.parse_args()


def canonical_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(
        config, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    args = parse_args()
    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if world_size != 3:
        raise SystemExit(f"expected world size 3, found {world_size}")
    if args.hidden_size % world_size:
        raise SystemExit(
            f"hidden_size={args.hidden_size} is not divisible by TP={world_size}"
        )
    if min(
        args.batch_size,
        args.input_size,
        args.hidden_size,
        args.output_size,
    ) < 1:
        raise SystemExit("all dimensions must be positive")

    seed = args.seed + (1 if os.environ.get("TOY_MISMATCH_RANK") == str(rank) else 0)
    config = {
        "batch_size": args.batch_size,
        "input_size": args.input_size,
        "hidden_size": args.hidden_size,
        "output_size": args.output_size,
        "seed": seed,
    }
    config_hash = canonical_hash(config)

    if args.backend == "nccl":
        if not torch.cuda.is_available():
            raise SystemExit("NCCL requested but CUDA unavailable")
        torch.cuda.set_device(local_rank)
        device = torch.device("cuda", local_rank)
    else:
        device = torch.device("cpu")
    dist.init_process_group(
        args.backend,
        timeout=timedelta(seconds=args.timeout_seconds),
    )
    hashes: list[Any] = [None for _ in range(world_size)]
    dist.all_gather_object(hashes, config_hash)
    if len(set(hashes)) != 1:
        raise RuntimeError(f"configuration hash mismatch across ranks: {hashes}")

    torch.manual_seed(seed)
    input_tensor = torch.randn(
        args.batch_size, args.input_size, dtype=torch.float32
    )
    weight1 = torch.randn(
        args.input_size, args.hidden_size, dtype=torch.float32
    )
    bias1 = torch.randn(args.hidden_size, dtype=torch.float32)
    weight2 = torch.randn(
        args.hidden_size, args.output_size, dtype=torch.float32
    )
    bias2 = torch.randn(args.output_size, dtype=torch.float32)
    reference = torch.relu(input_tensor @ weight1 + bias1) @ weight2 + bias2

    shard = args.hidden_size // world_size
    start = rank * shard
    end = start + shard
    local_input = input_tensor.to(device)
    local_weight1 = weight1[:, start:end].to(device)
    local_bias1 = bias1[start:end].to(device)
    local_weight2 = weight2[start:end, :].to(device)
    output_bias = bias2.to(device)

    dist.barrier()
    if device.type == "cuda":
        torch.cuda.synchronize()
    started = time.perf_counter()
    local_hidden = torch.relu(local_input @ local_weight1 + local_bias1)
    partial_output = local_hidden @ local_weight2
    dist.all_reduce(partial_output, op=dist.ReduceOp.SUM)
    distributed_output = partial_output + output_bias
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed_ms = (time.perf_counter() - started) * 1000

    error = (
        distributed_output.cpu() - reference
    ).abs().max().item()
    passed = torch.allclose(
        distributed_output.cpu(), reference, rtol=1e-5, atol=1e-6
    )
    rank_record = {
        "rank": rank,
        "hostname": socket.gethostname(),
        "config_hash": config_hash,
        "hidden_range": [start, end],
        "shapes": {
            "input": list(local_input.shape),
            "weight1_shard": list(local_weight1.shape),
            "hidden_shard": list(local_hidden.shape),
            "weight2_shard": list(local_weight2.shape),
            "partial_output": list(partial_output.shape),
        },
        "elapsed_ms": elapsed_ms,
        "passed": passed,
    }
    log("rank_shard", **rank_record)
    records: list[Any] = [None for _ in range(world_size)]
    dist.all_gather_object(records, rank_record)
    summary = {
        "schema_version": 1,
        "experiment_id": "lesson-28-toy-tp",
        "strategy": "toy-sharding",
        "correctness": {
            "passed": all(item["passed"] for item in records)
            and len({item["config_hash"] for item in records}) == 1
        },
        "environment": {
            "backend": args.backend,
            "world_size": world_size,
            "torch_version": torch.__version__,
            "device_type": device.type,
        },
        "model": config,
        "measurements": {
            "hidden_per_rank": shard,
            "max_absolute_error": error,
            "reference_output": reference.tolist(),
            "distributed_output": distributed_output.cpu().tolist(),
        },
        "ranks": sorted(records, key=lambda item: item["rank"]),
        "limitations": [
            "full deterministic weights are materialized on every rank",
            "toy MLP communication does not represent a complete transformer",
        ],
    }
    if rank == 0:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("TOY_TP_SUMMARY=" + json.dumps(summary, sort_keys=True))
    dist.barrier()
    dist.destroy_process_group()
    return 0 if summary["correctness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
