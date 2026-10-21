# 18 — Batching, scheduling, and paged attention

**Status:** outline
**Time:** 5 hours
**Compute:** `g1`, approximately 120 GPU-minutes
**Prerequisites:** 17

## Why this matters

Serving engines trade latency, fairness, memory utilization, and throughput
through scheduling and KV-block allocation.

## Learning outcomes

- Compare static, dynamic, and continuous batching.
- Explain iteration-level scheduling and head-of-line blocking.
- Explain logical/physical KV blocks and fragmentation.

## Under the hood

Trace request admission, token budgets, sequence scheduling, block allocation,
preemption, and eviction.

## Lab outline

1. Generate steady and bursty workloads.
2. Sweep sequence and batched-token limits.
3. Observe queue and KV-block occupancy.
4. Create a fairness or starvation scenario.

## Evidence to collect

- Scheduler timeline
- KV occupancy visualization
- Latency/throughput trade-off

## Completion gate

The learner can explain why a larger batch may improve throughput while worsening
tail latency.

## Cleanup

Stop workload and engine Pods and scale GPU capacity to zero.
