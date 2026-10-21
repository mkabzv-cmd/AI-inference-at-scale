# 29 — Pipeline-parallel large-model inference

**Status:** outline
**Time:** 1 day
**Compute:** `g3`, fixed GPU-hour budget
**Prerequisites:** 25–28

## Why this matters

Pipeline parallelism suits separate one-GPU nodes because it mostly communicates
activations at stage boundaries rather than collectives inside every layer.

## Learning outcomes

- Partition transformer layers across three stages.
- Explain stage memory, activation transfer, microbatches, and pipeline bubbles.
- Diagnose imbalance and slow-stage backpressure.

## Under the hood

Trace one request through `TP=1, PP=3`, including uneven layer partitioning,
prefill/decode stage handoff, and bubble formation.

## Lab outline

1. Validate PP with the tiny profile.
2. Run a quantized 30–32B profile.
3. Attempt the 70B-class 4-bit profile with short context/concurrency.
4. Sweep concurrency and stage balance.

## Evidence to collect

- Per-stage memory/utilization
- Network and pipeline timeline
- Fit/stability notes for each model profile

## Completion gate

One model larger than a single GPU runs across three nodes and its throughput
limitations are explained.

## Cleanup

Delete the distributed service, remove ephemeral caches, and scale nodes to zero.
