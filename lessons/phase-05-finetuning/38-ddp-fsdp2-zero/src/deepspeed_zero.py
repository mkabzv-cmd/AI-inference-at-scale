#!/usr/bin/env python3
"""Minimal real DeepSpeed ZeRO-3 training/checkpoint path."""

import argparse
import json
from pathlib import Path

import deepspeed
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--local_rank", type=int, default=-1)
    args = parser.parse_args()
    torch.manual_seed(3803)
    model = torch.nn.Sequential(
        torch.nn.Linear(256, 512),
        torch.nn.GELU(),
        torch.nn.Linear(512, 256),
    )
    engine, _, _, _ = deepspeed.initialize(
        model=model,
        model_parameters=model.parameters(),
        config=str(args.config),
    )
    losses = []
    for _ in range(args.steps):
        source = torch.randn(1, 256, device=engine.device)
        target = torch.randn(1, 256, device=engine.device)
        loss = torch.nn.functional.mse_loss(engine(source), target)
        engine.backward(loss)
        engine.step()
        losses.append(float(loss.detach().cpu()))
    tag = f"global-step-{args.steps}"
    engine.save_checkpoint(
        str(args.checkpoint),
        tag=tag,
        client_state={"schema_version": 1, "losses": losses},
    )
    if engine.global_rank == 0:
        print(json.dumps({"tag": tag, "losses": losses}, sort_keys=True))


if __name__ == "__main__":
    main()
