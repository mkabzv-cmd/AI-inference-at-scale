#!/usr/bin/env python3
"""Measure DataLoader delivery separately from model computation."""

import argparse
import json
import time
from pathlib import Path

import torch


class DeterministicRows(torch.utils.data.Dataset):
    def __init__(self, rows, dimension):
        self.rows = rows
        self.dimension = dimension

    def __len__(self):
        return self.rows

    def __getitem__(self, index):
        generator = torch.Generator().manual_seed(3701 + index)
        return torch.randn(self.dimension, generator=generator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=256)
    parser.add_argument("--dimension", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 0:
        raise SystemExit("workers cannot be negative")
    loader = torch.utils.data.DataLoader(
        DeterministicRows(args.rows, args.dimension),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        persistent_workers=args.workers > 0,
    )
    started = time.perf_counter()
    batches = 0
    checksum = 0.0
    for value in loader:
        checksum += float(value[:, 0].sum())
        batches += 1
    elapsed = time.perf_counter() - started
    report = {
        "schema_version": 1,
        "evidence_kind": "local-dataloader-probe-not-model-training",
        "workers": args.workers,
        "rows": args.rows,
        "dimension": args.dimension,
        "batch_size": args.batch_size,
        "batches": batches,
        "elapsed_seconds": elapsed,
        "batches_per_second": batches / elapsed,
        "checksum": checksum,
        "warning": (
            "Compare repeated runs on the target input pipeline; this synthetic "
            "probe does not predict language-model throughput."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
