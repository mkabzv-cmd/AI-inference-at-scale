#!/usr/bin/env python3
"""Correctness-first NCCL microbenchmark for three one-GPU ranks."""

from __future__ import annotations

import argparse
import json
import os
import socket
import statistics
import time
from datetime import timedelta
from typing import Any

import torch
import torch.distributed as dist


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def parse_sizes(value: str) -> list[int]:
    sizes = [int(item) for item in value.split(",")]
    if not sizes or any(item < 4 or item % 4 for item in sizes):
        raise argparse.ArgumentTypeError(
            "sizes must be positive multiples of four bytes"
        )
    return sizes


def run_operation(
    operation: str,
    message_bytes: int,
    rank: int,
    world_size: int,
) -> tuple[bool, int]:
    elements = message_bytes // 4
    if operation == "all-reduce":
        tensor = torch.full(
            (elements,), float(rank + 1), device="cuda", dtype=torch.float32
        )
        dist.all_reduce(tensor)
        expected = world_size * (world_size + 1) / 2
        return bool(torch.all(tensor == expected).item()), message_bytes

    if operation == "all-to-all":
        if elements < world_size:
            raise ValueError(
                "all-to-all message needs at least one element per rank"
            )
        elements -= elements % world_size
        chunk = elements // world_size
        pieces = [
            torch.full(
                (chunk,),
                float(rank * 100 + destination),
                device="cuda",
                dtype=torch.float32,
            )
            for destination in range(world_size)
        ]
        source = torch.cat(pieces)
        output = torch.empty_like(source)
        dist.all_to_all_single(output, source)
        observed = [
            output[source_rank * chunk].item()
            for source_rank in range(world_size)
        ]
        expected = [
            float(source_rank * 100 + rank)
            for source_rank in range(world_size)
        ]
        return observed == expected, source.numel() * source.element_size()

    tensor = torch.full(
        (elements,), 7.0 if rank == 0 else -1.0, device="cuda"
    )
    if rank == 0:
        dist.send(tensor, dst=1)
        dist.recv(tensor, src=1)
    elif rank == 1:
        dist.recv(tensor, src=0)
        tensor.add_(1.0)
        dist.send(tensor, dst=0)
    dist.barrier()
    passed = rank != 0 or bool(torch.all(tensor == 8.0).item())
    return passed, message_bytes * 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--operations",
        default="ping-pong,all-reduce,all-to-all",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("1024,65536,1048576,16777216"),
    )
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    operations = args.operations.split(",")
    allowed = {"ping-pong", "all-reduce", "all-to-all"}
    if not set(operations) <= allowed:
        raise SystemExit(f"operations must be from {sorted(allowed)}")
    if args.warmup < 0 or args.iterations < 2:
        raise SystemExit("warmup must be nonnegative; iterations >= 2")

    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if world_size != 3:
        raise SystemExit(f"this lab requires world size 3, found {world_size}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable")
    torch.cuda.set_device(local_rank)
    dist.init_process_group(
        "nccl",
        timeout=timedelta(seconds=args.timeout_seconds),
    )
    log(
        "environment",
        rank=rank,
        hostname=socket.gethostname(),
        torch_version=torch.__version__,
        cuda_version=torch.version.cuda,
        nccl_version=torch.cuda.nccl.version(),
        device=torch.cuda.get_device_name(local_rank),
    )

    all_correct = True
    for operation in operations:
        for size in args.sizes:
            samples = []
            passed = True
            logical_payload = size
            for iteration in range(args.warmup + args.iterations):
                dist.barrier()
                torch.cuda.synchronize()
                started = time.perf_counter()
                correct, logical_payload = run_operation(
                    operation, size, rank, world_size
                )
                torch.cuda.synchronize()
                elapsed = time.perf_counter() - started
                passed = passed and correct
                if iteration >= args.warmup:
                    samples.append(elapsed)

            records: list[Any] = [None for _ in range(world_size)]
            local = {
                "rank": rank,
                "hostname": socket.gethostname(),
                "passed": passed,
                "samples_seconds": samples,
            }
            dist.all_gather_object(records, local)
            operation_correct = all(item["passed"] for item in records)
            all_correct = all_correct and operation_correct
            if rank == 0:
                median_seconds = max(
                    statistics.median(item["samples_seconds"])
                    for item in records
                )
                payload_gbps = (
                    logical_payload * 8 / median_seconds / 1_000_000_000
                )
                bus_factor = (
                    2 * (world_size - 1) / world_size
                    if operation == "all-reduce"
                    else None
                )
                result = {
                    "operation": operation,
                    "message_bytes": size,
                    "logical_payload_bytes": logical_payload,
                    "world_size": world_size,
                    "median_seconds_slowest_rank": median_seconds,
                    "payload_gbps": payload_gbps,
                    "all_reduce_busbw_gbps_convention": (
                        payload_gbps * bus_factor
                        if bus_factor is not None
                        else None
                    ),
                    "correctness_passed": operation_correct,
                    "ranks": records,
                }
                log("BENCHMARK_RESULT", **result)

    dist.barrier()
    dist.destroy_process_group()
    return 0 if all_correct else 1


if __name__ == "__main__":
    raise SystemExit(main())
