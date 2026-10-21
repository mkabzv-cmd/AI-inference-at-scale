# Phase 3 — Inference optimization internals

Study memory accounting, scheduling, paging, quantization, kernels, compilation,
caching, and speculative decoding through controlled measurements.

These lessons are roadmap outlines, not runnable teaching material yet:

| Lesson | Planned outcome |
|---|---|
| [17 — Prefill, decode, and memory](17-prefill-decode-memory-accounting/) | Predict and measure model, activation, workspace, and KV-cache memory |
| [18 — Batching and paged attention](18-batching-scheduling-paged-attention/) | Observe queueing, scheduling, and KV-block allocation |
| [19 — Quantization trade-offs](19-quantization-systems-tradeoffs/) | Compare memory, speed, and quality under one workload |
| [20 — Kernels, compilation, and graphs](20-attention-kernels-compilation-cuda-graphs/) | Connect profiler evidence to launches and data movement |
| [21 — Cache and speculative techniques](21-prefix-cache-chunked-prefill-speculative/) | Demonstrate both wins and regressions from advanced decoding controls |
| [22 — Disciplined tuning](22-disciplined-tuning-workflow/) | Diagnose supplied pathologies with controlled experiments |
| [23 — Optimization capstone](23-capstone-optimize-under-slo/) | Meet an SLO with ablations, a quality gate, and documented limitations |
