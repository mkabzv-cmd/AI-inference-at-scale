#!/usr/bin/env python3
"""Record CPU/PyTorch/CUDA facts and optional nvidia-smi topology."""

import argparse
import json
import platform
import shutil
import subprocess
from pathlib import Path

import torch

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path)
args = parser.parse_args()

gpus = []
for index in range(torch.cuda.device_count()):
    properties = torch.cuda.get_device_properties(index)
    gpus.append(
        {
            "index": index,
            "name": properties.name,
            "total_vram_bytes": properties.total_memory,
            "total_vram_gib": properties.total_memory / 1024 ** 3,
            "compute_capability": [
                properties.major,
                properties.minor,
            ],
        }
    )

topology = None
if shutil.which("nvidia-smi"):
    completed = subprocess.run(
        ["nvidia-smi", "topo", "-m"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    topology = {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
topology_succeeded = topology is not None and topology["returncode"] == 0

report = {
    "schema_version": 1,
    "platform": platform.platform(),
    "machine": platform.machine(),
    "python": platform.python_version(),
    "torch": torch.__version__,
    "torch_cuda_build": torch.version.cuda,
    "torch_cuda_available": torch.cuda.is_available(),
    "selected_benchmark_device": "cuda" if torch.cuda.is_available() else "cpu",
    "gpus": gpus,
    "nvidia_smi_topology": topology,
    "nvidia_smi_topology_succeeded": topology_succeeded,
}

print(f"torch CUDA available: {torch.cuda.is_available()}")
print(f"selected benchmark device: {report['selected_benchmark_device']}")
for gpu in gpus:
    print(f"GPU {gpu['index']}: {gpu['name']}")
    print(f"VRAM total: {gpu['total_vram_gib']:.3f} GiB")
print(f"nvidia-smi topology succeeded: {topology_succeeded}")

if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"report written to {args.output}")
else:
    print(json.dumps(report, indent=2))
