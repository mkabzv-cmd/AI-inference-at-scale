# 25 — Parallelism taxonomy and arithmetic

**Status:** outline
**Time:** 4 hours
**Compute:** `local-cpu`
**Prerequisites:** 24

## Why this matters

GPU count alone does not determine a valid layout; model dimensions, memory,
communication, and workload matter.

## Learning outcomes

- Distinguish DP, TP, PP, sequence/context parallelism, and EP.
- Estimate per-rank memory and communication.
- Check attention-head, hidden-size, vocabulary, and quantization divisibility.

## Under the hood

Derive the tensors communicated by row/column sharding, pipeline boundaries,
replicas, and expert routing.

## Lab outline

1. Build a topology-planning worksheet or script.
2. Evaluate several model/configuration candidates.
3. Explain why three GPUs are natural for PP but awkward for many TP layouts.
4. Propose a four-GPU hybrid extension.

## Evidence to collect

- Topology planner
- Memory and traffic estimates
- Rejected-layout explanations

## Completion gate

The learner rejects invalid layouts before provisioning hardware.

## Cleanup

No cloud resources are required.
