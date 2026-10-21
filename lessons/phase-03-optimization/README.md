# Phase 3 — Inference optimization internals

Study memory accounting, scheduling, paging, quantization, kernels, compilation,
caching, and speculative decoding through controlled measurements.

These are practical `draft` lessons. Every lesson has a dependency-free CPU
mechanism path, explicit evidence contract, deliberate failure, solutions, and
an optional bounded GPU path. CPU simulations and synthetic fixtures are
labelled so they cannot be mistaken for hardware measurements. The GPU/EKS
paths require execution and independent review before publication.

| Lesson | Practical outcome |
|---|---|
| [17 — Prefill, decode, and memory](17-prefill-decode-memory-accounting/) | Derive tensor shapes and KV/VRAM budgets, simulate a safe OOM boundary, then reconcile optional engine evidence |
| [18 — Batching and paged attention](18-batching-scheduling-paged-attention/) | Trace static/continuous scheduling and physical KV pages in a per-tick timeline |
| [19 — Quantization trade-offs](19-quantization-systems-tradeoffs/) | Quantize a real toy layer, account for metadata, enforce quality, and design a fair artifact/kernel comparison |
| [20 — Kernels, compilation, and graphs](20-attention-kernels-compilation-cuda-graphs/) | Implement online attention, calculate IO, and separate fusion, compilation, capture, and replay evidence |
| [21 — Cache and speculative techniques](21-prefix-cache-chunked-prefill-speculative/) | Simulate cache isolation, chunk scheduling, and exact draft verification; test favorable and unfavorable distributions |
| [22 — Disciplined tuning](22-disciplined-tuning-workflow/) | Diagnose queue/KV/client pathologies, render controlled runs, and reject a confounded speedup |
| [23 — Optimization capstone](23-capstone-optimize-under-slo/) | Deploy one digest-pinned GPU Pod, benchmark bounded candidates, apply hard SLO gates, ablate, break/repair, and clean up |

Recommended order is 17 through 23. Do not start the capstone until lesson 12's
benchmark vocabulary and lessons 17–22's mechanism gates are comfortable.
