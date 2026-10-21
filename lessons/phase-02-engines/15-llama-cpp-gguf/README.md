# 15 — llama.cpp and GGUF

**Status:** outline
**Time:** 5 hours
**Compute:** `local-cpu` and optional `g1`
**Prerequisites:** 12

## Why this matters

llama.cpp exposes quantization, memory mapping, and CPU/GPU placement through a
different and highly portable runtime design.

## Learning outcomes

- Explain GGUF metadata and common quantization families.
- Control CPU/GPU layer placement and memory mapping.
- Compare portability and quality/performance trade-offs.

## Under the hood

Trace model-file mapping, tensor placement, dequantization, prompt processing,
and token generation across CPU and GPU.

## Lab outline

1. Obtain or create a pinned GGUF artifact.
2. Run `llama-server` and `llama-bench`.
3. Sweep quantization and GPU offload.
4. Compare against the shared PyTorch-engine workload where valid.

## Evidence to collect

- Artifact metadata and provenance
- Offload/quantization results
- Runtime architecture comparison

## Completion gate

The learner explains when GGUF portability is more important than maximum server
throughput.

## Cleanup

Stop the server and remove only caches explicitly marked temporary.
