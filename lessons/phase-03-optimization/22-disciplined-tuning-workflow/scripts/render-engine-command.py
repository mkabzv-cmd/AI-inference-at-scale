#!/usr/bin/env python3
"""Render, but do not execute, one reviewed vLLM experiment command."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--matrix", type=Path, default=Path("configs/experiment-matrix.json"))
parser.add_argument("--experiment", required=True)
parser.add_argument("--image", required=True)
args = parser.parse_args()
if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}",
    args.image,
):
    raise SystemExit("--image must be an immutable name@sha256 digest")
matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
experiment = next(
    (item for item in matrix["experiments"] if item["id"] == args.experiment),
    None,
)
if experiment is None:
    raise SystemExit("unknown experiment")
if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", experiment["id"]):
    raise SystemExit("experiment id is unsafe for a container name")
command = [
    "docker",
    "run",
    "--detach",
    "--rm",
    "--name",
    f"oms-l22-{experiment['id']}",
    "--gpus",
    "all",
    "--shm-size=4g",
    "--publish",
    "127.0.0.1:8000:8000",
    args.image,
    "Qwen/Qwen2.5-0.5B-Instruct",
    "--revision",
    matrix["frozen"]["model_revision"],
    "--served-model-name",
    "oms-model",
    "--dtype",
    "half",
    "--max-model-len",
    "4096",
    "--gpu-memory-utilization",
    str(experiment["gpu_memory_utilization"]),
    "--max-num-seqs",
    str(experiment["max_num_seqs"]),
    "--max-num-batched-tokens",
    str(experiment["max_num_batched_tokens"]),
]
print(" ".join(shlex.quote(item) for item in command))
