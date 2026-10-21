# 14 — SGLang on one GPU

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 90 GPU-minutes
**Prerequisites:** 12, 13

## Why this matters

Comparing two serious engines reveals alternative scheduler, cache, and
structured-generation designs.

## Learning outcomes

- Serve the common model and API workload with SGLang.
- Explain cache-aware scheduling and radix-prefix reuse conceptually.
- Identify compatibility boundaries rather than hiding them.

## Under the hood

Compare request scheduling, prefix representation, memory allocation, and
structured-output execution with the vLLM path.

## Lab outline

1. Deploy a pinned SGLang image.
2. Replay the shared benchmark.
3. Run repeated-prefix and structured-output workloads.
4. Record unsupported or fallback paths.

## Evidence to collect

- Comparable results
- Cache/scheduler diagram
- Compatibility notes

## Completion gate

The learner can select between the two engines for a stated workload without
using popularity as evidence.

## Cleanup

Delete the release, temporary caches, and GPU capacity.
