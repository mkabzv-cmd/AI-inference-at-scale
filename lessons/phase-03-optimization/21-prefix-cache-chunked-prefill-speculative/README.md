# 21 — Prefix caching, chunked prefill, and speculative decoding

**Status:** outline
**Time:** 6 hours
**Compute:** `g1`, approximately 180 GPU-minutes
**Prerequisites:** 18–20

## Why this matters

Reuse and look-ahead optimizations can transform some workloads and harm others.

## Learning outcomes

- Explain prefix-cache keys, isolation, hits, eviction, and saved prefill.
- Explain chunked prefill and scheduler interaction.
- Explain draft/target speculative decoding and acceptance rate.

## Under the hood

Trace shared-prefix blocks, prefill chunks, draft tokens, verification, rejection,
and extra memory.

## Lab outline

1. Build workloads with repeated and unique prefixes.
2. Compare chunked and unchunked prefill.
3. Run speculative decoding with useful and poor draft behavior.
4. Measure hit/acceptance rates and tail latency.

## Evidence to collect

- Workload definitions
- Cache/acceptance metrics
- Win/loss explanation

## Completion gate

The learner predicts which request distribution benefits from each optimization.

## Cleanup

Clear temporary caches, delete deployments, and scale GPU capacity to zero.
