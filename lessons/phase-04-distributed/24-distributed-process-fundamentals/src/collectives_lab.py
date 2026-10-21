#!/usr/bin/env python3
"""Run small, correctness-checked torch.distributed operations."""

from __future__ import annotations

import argparse
import json
import os
import socket
import statistics
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist


OPERATIONS = (
    "broadcast",
    "all-gather",
    "all-reduce",
    "reduce-scatter",
    "send-recv",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=OPERATIONS, default="all-reduce")
    parser.add_argument(
        "--backend", choices=("auto", "gloo", "nccl"), default="auto"
    )
    parser.add_argument("--elements", type=int, default=1024)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--expect-world-size", type=int, default=3)
    parser.add_argument("--mismatch-rank", type=int, default=-1)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/local")
    )
    return parser.parse_args()


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def choose_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    return "nccl" if torch.cuda.is_available() else "gloo"


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def execute(
    operation: str,
    tensor: torch.Tensor,
    rank: int,
    world_size: int,
) -> tuple[bool, dict[str, Any]]:
    if operation == "broadcast":
        tensor.fill_(42.0 if rank == 0 else -1.0)
        dist.broadcast(tensor, src=0)
        passed = bool(torch.all(tensor == 42.0).item())
        return passed, {
            "expected_first": 42.0,
            "observed_first": tensor[0].item(),
        }

    if operation == "all-gather":
        tensor.fill_(float(rank + 1))
        outputs = [torch.empty_like(tensor) for _ in range(world_size)]
        dist.all_gather(outputs, tensor)
        observed = [item[0].item() for item in outputs]
        expected = [float(item + 1) for item in range(world_size)]
        passed = observed == expected
        return passed, {
            "expected_markers": expected,
            "observed_markers": observed,
        }

    if operation == "all-reduce":
        tensor.fill_(float(rank + 1))
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
        expected = world_size * (world_size + 1) / 2
        passed = bool(torch.all(tensor == expected).item())
        return passed, {
            "expected_first": expected,
            "observed_first": tensor[0].item(),
        }

    if operation == "reduce-scatter":
        output = torch.empty_like(tensor)
        input_tensor = torch.full(
            (world_size * tensor.numel(),),
            float(rank + 1),
            dtype=tensor.dtype,
            device=tensor.device,
        )
        dist.reduce_scatter_tensor(
            output, input_tensor, op=dist.ReduceOp.SUM
        )
        expected = world_size * (world_size + 1) / 2
        passed = bool(torch.all(output == expected).item())
        return passed, {
            "expected_first": expected,
            "observed_first": output[0].item(),
            "output_elements": output.numel(),
        }

    if world_size < 2:
        raise ValueError("send-recv requires at least two ranks")
    last_rank = world_size - 1
    tensor.fill_(123.0 if rank == 0 else -1.0)
    if rank == 0:
        dist.send(tensor, dst=last_rank)
    elif rank == last_rank:
        dist.recv(tensor, src=0)
    dist.barrier()
    passed = rank not in (0, last_rank) or tensor[0].item() == 123.0
    return passed, {
        "source": 0,
        "destination": last_rank,
        "observed_first": tensor[0].item(),
    }


def main() -> int:
    args = parse_args()
    if args.elements < 1 or args.iterations < 1 or args.warmup < 0:
        raise SystemExit(
            "elements/iterations must be positive; warmup nonnegative"
        )
    if args.timeout_seconds < 3:
        raise SystemExit("timeout-seconds must be at least 3")

    backend = choose_backend(args.backend)
    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if world_size != args.expect_world_size:
        raise SystemExit(
            f"world-size contract failed: expected {args.expect_world_size}, "
            f"launcher supplied {world_size}"
        )

    if backend == "nccl":
        if not torch.cuda.is_available():
            raise SystemExit(
                "NCCL requested but torch.cuda.is_available() is false"
            )
        torch.cuda.set_device(local_rank)
        device = torch.device("cuda", local_rank)
    else:
        device = torch.device("cpu")

    log(
        "rank_environment",
        rank=rank,
        local_rank=local_rank,
        world_size=world_size,
        backend=backend,
        hostname=socket.gethostname(),
        device=str(device),
    )
    dist.init_process_group(
        backend=backend,
        init_method="env://",
        timeout=timedelta(seconds=args.timeout_seconds),
    )

    operation = args.operation
    if rank == args.mismatch_rank:
        operation = (
            "broadcast" if args.operation != "broadcast" else "all-reduce"
        )
    log("operation_enter", rank=rank, operation=operation)

    tensor = torch.empty(
        args.elements, dtype=torch.float32, device=device
    )
    timings_ms = []
    last_detail: dict[str, Any] = {}
    correctness = True
    for iteration in range(args.warmup + args.iterations):
        dist.barrier()
        synchronize(device)
        started = time.perf_counter()
        passed, detail = execute(operation, tensor, rank, world_size)
        synchronize(device)
        elapsed_ms = (time.perf_counter() - started) * 1000
        correctness = correctness and passed
        last_detail = detail
        if iteration >= args.warmup:
            timings_ms.append(elapsed_ms)

    record = {
        "rank": rank,
        "local_rank": local_rank,
        "world_size": world_size,
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "backend": backend,
        "device": str(device),
        "operation": operation,
        "elements": args.elements,
        "dtype": str(tensor.dtype),
        "payload_bytes": tensor.numel() * tensor.element_size(),
        "iterations": args.iterations,
        "timing_ms": {
            "median": statistics.median(timings_ms),
            "minimum": min(timings_ms),
            "maximum": max(timings_ms),
            "samples": timings_ms,
        },
        "correctness": {"passed": correctness, "detail": last_detail},
    }

    gathered: list[Any] = [None for _ in range(world_size)]
    dist.all_gather_object(gathered, record)
    summary = {
        "schema_version": 1,
        "experiment_id": os.environ.get("EXPERIMENT_ID", "lesson-24"),
        "strategy": "collective",
        "operation": args.operation,
        "correctness": {
            "passed": all(
                item["correctness"]["passed"] for item in gathered
            )
            and len({item["rank"] for item in gathered}) == world_size
        },
        "environment": {
            "world_size": world_size,
            "backend": backend,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
        },
        "measurements": {
            "payload_bytes_per_rank": record["payload_bytes"],
            "rank_median_ms": {
                str(item["rank"]): item["timing_ms"]["median"]
                for item in gathered
            },
        },
        "ranks": sorted(gathered, key=lambda item: item["rank"]),
        "limitations": [
            "payload bytes are not physical wire-byte measurements",
            "microbenchmark timings do not predict engine throughput",
        ],
    }

    log("RESULT_JSON", **record)
    if rank == 0:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / "summary.json"
        output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log(
            "summary_written",
            path=str(output),
            passed=summary["correctness"]["passed"],
        )

    dist.barrier()
    dist.destroy_process_group()
    return 0 if summary["correctness"]["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        log(
            "rank_failed",
            error_type=type(error).__name__,
            message=str(error),
        )
        raise
