#!/usr/bin/env python3
"""Minimal FSDP2 full-shard step and distributed checkpoint example."""

import argparse
import json
import os
from pathlib import Path

import torch
import torch.distributed as dist
import torch.distributed.checkpoint as dcp
from torch.distributed.fsdp import fully_shard


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = torch.nn.ModuleList(
            [torch.nn.Linear(256, 256) for _ in range(4)]
        )

    def forward(self, value):
        for layer in self.layers:
            value = torch.nn.functional.gelu(layer(value))
        return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()
    dist.init_process_group("nccl")
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    torch.manual_seed(3802)
    model = TinyModel().cuda()
    for layer in model.layers:
        fully_shard(layer)
    fully_shard(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    source = torch.randn(2, 256, device="cuda")
    target = torch.randn(2, 256, device="cuda")
    loss = torch.nn.functional.mse_loss(model(source), target)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    state = {"model": model.state_dict(), "optimizer": optimizer.state_dict()}
    dcp.save(state, checkpoint_id=str(args.checkpoint))
    dist.barrier()
    if dist.get_rank() == 0:
        (args.checkpoint / "course-metadata.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "world_size_at_save": dist.get_world_size(),
                    "checkpoint_api": "torch.distributed.checkpoint",
                    "restore_rule": "all ranks load before training resumes"
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print("PASS: FSDP2 sharded state saved")
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
