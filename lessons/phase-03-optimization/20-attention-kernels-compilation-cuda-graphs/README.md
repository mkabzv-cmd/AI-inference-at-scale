# 20 — Attention kernels, compilation, and CUDA graphs

**Status:** outline
**Time:** 6 hours
**Compute:** `g1`, approximately 150 GPU-minutes
**Prerequisites:** 17

## Why this matters

Kernel fusion, IO-aware attention, compilation, and graph capture attack different
forms of overhead and have different shape constraints.

## Learning outcomes

- Distinguish eager execution, fused kernels, compilation, and graph replay.
- Explain why FlashAttention-style designs reduce memory traffic.
- Identify warmup, fallback, and dynamic-shape costs.

## Under the hood

Compare profiler traces at the kernel-launch and memory-movement level.

## Lab outline

1. Capture an eager baseline trace.
2. Switch attention backend or fused path.
3. Compare compiled/graph and eager modes.
4. Vary shapes to trigger fallback or recapture.

## Evidence to collect

- Profiler traces
- Launch-count and timing comparison
- Compatibility boundary

## Completion gate

The learner points to the eliminated or changed operations that explain the
result.

## Cleanup

Stop profiler and engine workloads; remove temporary traces if not retained.
