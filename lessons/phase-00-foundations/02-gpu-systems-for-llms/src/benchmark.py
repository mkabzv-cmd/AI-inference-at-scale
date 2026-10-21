#!/usr/bin/env python3
"""Small synchronized matmul and device-copy benchmark."""

import argparse
import json
import statistics
import time
from pathlib import Path

import torch


def platform_processor_name():
    return "CPU"


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def measure(operation, device, warmup, iterations):
    for _ in range(warmup):
        operation()
    synchronize(device)
    samples = []
    for _ in range(iterations):
        synchronize(device)
        start = time.perf_counter()
        operation()
        synchronize(device)
        samples.append((time.perf_counter() - start) * 1000)
    return samples


parser = argparse.ArgumentParser()
parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
parser.add_argument("--matrix-size", type=int, default=1024)
parser.add_argument("--copy-mebibytes", type=int, default=64)
parser.add_argument("--warmup", type=int, default=3)
parser.add_argument("--iterations", type=int, default=10)
parser.add_argument("--output", type=Path)
args = parser.parse_args()

for name in ("matrix_size", "copy_mebibytes", "iterations"):
    if getattr(args, name) < 1:
        parser.error(f"--{name.replace('_', '-')} must be at least 1")
if args.warmup < 0:
    parser.error("--warmup cannot be negative")

requested = args.device
if requested == "auto":
    requested = "cuda" if torch.cuda.is_available() else "cpu"
if requested == "cuda" and not torch.cuda.is_available():
    raise SystemExit("CUDA requested, but torch.cuda.is_available() is false")
device = torch.device(requested)

matrix_bytes = 3 * args.matrix_size ** 2 * 4
copy_bytes = args.copy_mebibytes * 1024 ** 2
print(f"planned matmul tensors: {matrix_bytes / 1024 ** 2:.1f} MiB")
print(f"planned copy payload:   {copy_bytes / 1024 ** 2:.1f} MiB")

a = torch.randn((args.matrix_size, args.matrix_size), device=device)
b = torch.randn((args.matrix_size, args.matrix_size), device=device)
c = torch.empty_like(a)


def matmul():
    torch.mm(a, b, out=c)


element_count = copy_bytes // 4
source = torch.randn(element_count, dtype=torch.float32, device=device)
destination = torch.empty_like(source)


def copy():
    destination.copy_(source)


matmul_samples = measure(matmul, device, args.warmup, args.iterations)
copy_samples = measure(copy, device, args.warmup, args.iterations)
matmul_ms = statistics.median(matmul_samples)
copy_ms = statistics.median(copy_samples)

operations = 2 * args.matrix_size ** 3
gflops = operations / (matmul_ms / 1000) / 1e9
payload_gbps = copy_bytes / (copy_ms / 1000) / 1e9
device_name = (
    torch.cuda.get_device_name(device)
    if device.type == "cuda"
    else platform_processor_name()
)

result = {
    "schema_version": 1,
    "torch": torch.__version__,
    "device": {"type": device.type, "name": device_name},
    "settings": {
        "warmup": args.warmup,
        "iterations": args.iterations,
        "dtype": "float32",
    },
    "matmul": {
        "matrix_size": args.matrix_size,
        "median_ms": matmul_ms,
        "samples_ms": matmul_samples,
        "approx_gflops": gflops,
    },
    "copy": {
        "mebibytes": args.copy_mebibytes,
        "median_ms": copy_ms,
        "samples_ms": copy_samples,
        "approx_gigabytes_per_second": payload_gbps,
        "counting_convention": "payload bytes divided by elapsed time",
    },
}

print(f"device: {device_name}")
print(f"matmul median: {matmul_ms:.3f} ms ({gflops:.3f} GFLOP/s)")
print(f"copy median:   {copy_ms:.3f} ms ({payload_gbps:.3f} GB/s payload)")
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"result written to {args.output}")
else:
    print(json.dumps(result, indent=2))
