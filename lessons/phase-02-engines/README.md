# Phase 2 — Single-GPU inference engines

Establish a transparent baseline, build a fair benchmark, and compare vLLM,
SGLang, llama.cpp, and Transformers using one controlled workload.

These lessons are roadmap outlines, not runnable teaching material yet:

| Lesson | Planned outcome |
|---|---|
| [11 — Transformers baseline](11-transformers-baseline/) | Build the readable reference server and trace one request |
| [12 — Benchmarking methodology](12-benchmarking-methodology/) | Define a shared workload, result schema, warm-up, correctness gate, and baseline |
| [13 — vLLM on one GPU](13-vllm-one-gpu/) | Deploy vLLM and explain its scheduler and memory metrics |
| [14 — SGLang on one GPU](14-sglang-one-gpu/) | Run the equivalent workload and compare scheduler/cache behavior |
| [15 — llama.cpp and GGUF](15-llama-cpp-gguf/) | Measure quantization, memory mapping, and CPU/GPU offload |
| [16 — Engine shootout capstone](16-capstone-engine-shootout/) | Produce a reproducible engine decision record |
