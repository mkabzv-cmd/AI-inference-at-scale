#!/usr/bin/env python3
"""Real torch.distributed DDP equivalence check for three CPU or GPU ranks."""

import argparse
import json
import os
from pathlib import Path

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("gloo", "nccl"), default="gloo")
    args = parser.parse_args()
    dist.init_process_group(backend=args.backend)
    rank = dist.get_rank()
    world = dist.get_world_size()
    if world != 3:
        raise SystemExit("this study requires exactly three ranks")
    device = (
        torch.device("cuda", int(os.environ["LOCAL_RANK"]))
        if args.backend == "nccl"
        else torch.device("cpu")
    )
    if device.type == "cuda":
        torch.cuda.set_device(device)
    torch.manual_seed(3801)
    model = torch.nn.Linear(1, 1, bias=False).to(device)
    with torch.no_grad():
        model.weight.fill_(-0.75)
    wrapped = DistributedDataParallel(
        model,
        device_ids=[device.index] if device.type == "cuda" else None,
    )
    optimizer = torch.optim.SGD(wrapped.parameters(), lr=0.05)
    local_x = torch.tensor(
        [[rank * 2.0 + 1.0], [rank * 2.0 + 2.0]], device=device
    )
    local_y = 2.0 * local_x
    loss = torch.nn.functional.mse_loss(wrapped(local_x), local_y) / 2.0
    loss.backward()
    optimizer.step()
    ddp_weight = model.weight.detach().clone()

    gathered = [torch.zeros_like(ddp_weight) for _ in range(world)]
    dist.all_gather(gathered, ddp_weight)
    if rank == 0:
        reference = torch.nn.Linear(1, 1, bias=False).to(device)
        with torch.no_grad():
            reference.weight.fill_(-0.75)
        reference_optimizer = torch.optim.SGD(
            reference.parameters(), lr=0.05
        )
        global_x = torch.arange(1.0, 7.0, device=device).reshape(-1, 1)
        global_y = 2.0 * global_x
        reference_loss = (
            torch.nn.functional.mse_loss(reference(global_x), global_y) / 2.0
        )
        reference_loss.backward()
        reference_optimizer.step()
        difference = abs(
            float(ddp_weight.cpu()) - float(reference.weight.detach().cpu())
        )
        assert difference < 1e-6
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "world_size": world,
                    "backend": args.backend,
                    "ddp_rank_weights": [float(value.cpu()) for value in gathered],
                    "single_process_weight": float(
                        reference.weight.detach().cpu()
                    ),
                    "maximum_difference": difference,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print("PASS: DDP update equals a single global-batch update")
    dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
