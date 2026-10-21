# 02 — GPU systems for LLMs

**Status:** outline
**Time:** 3 hours
**Compute:** `local-cpu`, optional `g1`
**Prerequisites:** 01

## Why this matters

Model performance depends as much on memory movement and topology as on arithmetic
throughput.

## Learning outcomes

- Distinguish VRAM, host RAM, storage, compute, and memory bandwidth.
- Estimate weight memory at common precisions.
- Explain PCIe, NVLink, ordinary networking, and RDMA at a conceptual level.

## Under the hood

Follow bytes from storage to host memory, GPU memory, kernels, caches, and network
interfaces. Relate arithmetic intensity to compute- or bandwidth-bound behavior.

## Lab outline

1. Build a parameter/precision memory calculator.
2. Run matrix-multiply and memory-copy microbenchmarks.
3. Compare predicted and observed bottlenecks.

## Evidence to collect

- Memory worksheet
- Benchmark JSON
- Hardware hierarchy diagram

## Completion gate

Given a model size and precision, the learner can estimate whether weights fit
and name the next likely memory consumers.

## Cleanup

Stop any optional GPU process and return the node group to zero.
