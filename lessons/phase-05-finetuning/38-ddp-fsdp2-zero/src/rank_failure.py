#!/usr/bin/env python3
"""Intentional rank failure used to inspect launcher and Job behavior."""

import os
import sys
import time

import torch.distributed as dist


dist.init_process_group("gloo")
rank = dist.get_rank()
if rank == 1:
    print("intentional rank-1 exit", flush=True)
    sys.exit(42)
time.sleep(5)
dist.barrier()
