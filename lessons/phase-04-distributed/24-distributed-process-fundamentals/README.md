# 24 — Distributed-process fundamentals

**Status:** outline
**Time:** 5 hours
**Compute:** `local-cpu`, then `g3` for measurements
**Prerequisites:** 23

## Why this matters

Engines hide ranks and collectives, but distributed failures cannot be understood
without them.

## Learning outcomes

- Explain rank, local rank, world size, rendezvous, and process groups.
- Implement send/receive, broadcast, all-gather, reduce-scatter, and all-reduce.
- Predict synchronization and byte movement.

## Under the hood

Draw each collective as messages between ranks and derive its role in model or
gradient sharding.

## Lab outline

1. Write small `torch.distributed` programs locally.
2. Move them to two and three GPU nodes.
3. Add timing and byte counters.
4. Break rank count, ordering, and rendezvous deliberately.

## Evidence to collect

- Source and topology diagrams
- Collective timing results
- Failure diagnoses

## Completion gate

The learner can identify which collective a higher-level parallel strategy needs.

## Cleanup

Terminate every rank and return GPU desired capacity to zero.
