# 17 — Prefill, decode, and memory accounting

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 90 GPU-minutes
**Prerequisites:** 16

## Why this matters

Context length and concurrency often consume more memory than expected even when
the model weights fit.

## Learning outcomes

- Separate weight, activation, workspace, graph, and KV-cache memory.
- Derive a KV-cache estimate from model architecture and workload.
- Distinguish prefill and decode bottlenecks.

## Under the hood

Follow attention keys/values across layers and requests, including grouped-query
attention and cache dtype.

## Lab outline

1. Predict memory for several workloads.
2. Sweep context length and concurrency.
3. Trigger a controlled OOM.
4. Reconcile predicted and measured allocations.

## Evidence to collect

- Memory calculator
- OOM boundary results
- Prefill/decode profile

## Completion gate

The learner predicts which workload change will exhaust memory first and why.

## Cleanup

Terminate failed processes and return the GPU node group to zero.
