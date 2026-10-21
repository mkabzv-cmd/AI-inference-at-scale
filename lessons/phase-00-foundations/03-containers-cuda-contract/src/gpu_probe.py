#!/usr/bin/env python3
"""Report the container's CUDA visibility and perform a real tensor check."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import torch

parser = argparse.ArgumentParser()
parser.add_argument("--require-gpu", action="store_true")
parser.add_argument("--output", type=Path)
args = parser.parse_args()

visible_environment = {
    name: os.environ.get(name)
    for name in (
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
        "NVIDIA_DRIVER_CAPABILITIES",
    )
}

nvidia_smi = None
if shutil.which("nvidia-smi"):
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,driver_version,memory.total",
        "--format=csv,noheader",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    nvidia_smi = {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }

gpus = []
for index in range(torch.cuda.device_count()):
    properties = torch.cuda.get_device_properties(index)
    gpus.append(
        {
            "index": index,
            "name": properties.name,
            "vram_bytes": properties.total_memory,
            "compute_capability": [properties.major, properties.minor],
        }
    )

tensor_check = None
tensor_error = None
if torch.cuda.is_available():
    try:
        left = torch.tensor([2.0, 3.0], device="cuda:0")
        right = torch.tensor([4.0, 1.0], device="cuda:0")
        tensor_check = [(left * right).sum().cpu().item()]
    except Exception as error:  # evidence is deliberately serialized
        tensor_error = f"{type(error).__name__}: {error}"

result = {
    "schema_version": 1,
    "torch_version": torch.__version__,
    "torch_cuda_build": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "visible_gpu_count": torch.cuda.device_count(),
    "gpus": gpus,
    "environment": visible_environment,
    "nvidia_smi": nvidia_smi,
    "tensor_check": tensor_check,
    "tensor_error": tensor_error,
}

print(f"torch version: {torch.__version__}")
print(f"torch CUDA build: {torch.version.cuda}")
print(f"torch CUDA available: {torch.cuda.is_available()}")
print(f"visible GPU count: {torch.cuda.device_count()}")
for gpu in gpus:
    print(
        f"GPU {gpu['index']}: {gpu['name']} "
        f"capability={gpu['compute_capability']} "
        f"VRAM={gpu['vram_bytes'] / 1024 ** 3:.3f} GiB"
    )
if tensor_check is not None:
    print(f"tensor check: {tensor_check}")
if tensor_error is not None:
    print(f"tensor error: {tensor_error}")

if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"result written to {args.output}")

if args.require_gpu and not torch.cuda.is_available():
    print("ERROR: GPU was required but PyTorch sees no CUDA device.")
    raise SystemExit(3)
if args.require_gpu and tensor_check != [11.0]:
    print("ERROR: GPU was visible but the CUDA tensor check failed.")
    raise SystemExit(4)

print(
    "requirement: GPU present, probe completed"
    if args.require_gpu
    else "requirement: GPU optional, probe completed"
)
