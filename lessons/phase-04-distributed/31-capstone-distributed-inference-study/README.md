# 31 — Capstone: distributed-inference study

**Status:** outline
**Time:** 2–3 days
**Compute:** `g3`, approved GPU-hour budget
**Prerequisites:** 24–30

## Why this matters

The goal is a defensible distributed-systems study, not a single successful
command.

## Learning outcomes

- Design and execute comparable PP, TP, and DP experiments.
- Handle model staging, startup coordination, and partial failure.
- Report performance, cost, and limitations honestly.

## Under the hood

Connect NCCL baselines, engine traces, network bytes, GPU utilization, and
scheduler behavior to each observed result.

## Lab outline

1. Freeze model/workload/environment inputs.
2. Run the three parallel strategies.
3. Kill a worker or drain a node.
4. Repeat the most important result.
5. Write a production recommendation.

## Evidence to collect

- Raw NCCL and engine results
- Failure/recovery timeline
- GPU-hour cost and model-cache strategy
- Research-style report

## Completion gate

Another learner can reproduce the study and challenge its conclusions from the
published evidence.

## Cleanup

Remove services, jobs, caches, temporary storage, and all GPU capacity.
