#!/usr/bin/env python3
"""Capture a real torch.profiler trace for a small training step."""

import argparse
import json
from pathlib import Path

import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--dimension", type=int, default=2048)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the GPU profile path")
    device = torch.device("cuda")
    torch.manual_seed(3701)
    model = torch.nn.Sequential(
        torch.nn.Linear(args.dimension, args.dimension),
        torch.nn.GELU(),
        torch.nn.Linear(args.dimension, args.dimension),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    data = torch.randn(4, args.dimension, device=device)
    target = torch.randn(4, args.dimension, device=device)
    args.output.mkdir(parents=True, exist_ok=True)
    activities = [
        torch.profiler.ProfilerActivity.CPU,
        torch.profiler.ProfilerActivity.CUDA,
    ]
    with torch.profiler.profile(
        activities=activities,
        schedule=torch.profiler.schedule(wait=1, warmup=2, active=3, repeat=1),
        on_trace_ready=torch.profiler.tensorboard_trace_handler(
            str(args.output / "trace")
        ),
        record_shapes=True,
        profile_memory=True,
        with_stack=False,
    ) as profile:
        for step in range(args.steps):
            prediction = model(data)
            loss = torch.nn.functional.mse_loss(prediction, target)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            profile.step()
    summary = {
        "schema_version": 1,
        "steps": args.steps,
        "dimension": args.dimension,
        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "trace_directory": "trace",
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
