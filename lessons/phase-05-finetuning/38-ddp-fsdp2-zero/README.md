# 38 — Distributed training: DDP, FSDP2, and ZeRO

**Status:** outline
**Time:** 2 days
**Compute:** `g3`, approved training budget
**Prerequisites:** 24–27, 37

## Why this matters

Distributed training can replicate computation for throughput or shard states to
fit a model, and each choice creates different collectives and checkpoints.

## Learning outcomes

- Explain DDP gradient synchronization and why it does not pool model memory.
- Explain FSDP2 and ZeRO parameter/gradient/optimizer sharding.
- Compare all-reduce, all-gather, and reduce-scatter traffic.

## Under the hood

Trace a training step and checkpoint through DDP, FSDP2, and selected ZeRO stages.

## Lab outline

1. Verify DDP numerical equivalence on a tiny model.
2. Compare one, two, and three ranks.
3. Run FSDP2 and ZeRO on a memory-pressure case.
4. Kill a rank and restore a sharded checkpoint.

## Evidence to collect

- Per-rank memory and step time
- Communication traces
- Checkpoint/recovery notes

## Completion gate

The learner selects a strategy from memory, network, checkpoint, and throughput
requirements.

## Cleanup

Remove distributed jobs, temporary checkpoints, and all GPU capacity.
