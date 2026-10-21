# Phase 2 — Single-GPU inference engines

Build one readable reference server, learn to benchmark without hiding
queueing/quality failures, then deploy and compare vLLM, SGLang, and llama.cpp.

All six lessons are practical drafts with source, pinned artifacts, request
fixtures, evidence contracts, deliberate failures, verification, and cleanup.
Static/CPU checks do not replace a clean GPU/EKS run; read each validation
boundary before claiming results.

| Lesson | Practical outcome |
|---|---|
| [11 — Transformers baseline](11-transformers-baseline/) | Build a transparent FastAPI/Transformers GPU server and trace tokenization, prefill, decode, KV cache, streaming, cancellation, and serialized queueing |
| [12 — Benchmarking methodology](12-benchmarking-methodology/) | Run an auditable open/closed-loop SSE benchmark with frozen prompts, exact token counting, quality gates, raw records, and reports |
| [13 — vLLM on one GPU](13-vllm-one-gpu/) | Deploy vLLM 0.28.0 by digest, inspect scheduler/KV metrics, test a sequence-cap control, and recover from invalid memory configuration |
| [14 — SGLang on one GPU](14-sglang-one-gpu/) | Deploy SGLang 0.5.21, verify constrained JSON, study Radix prefix reuse, and compare cache enabled/disabled |
| [15 — llama.cpp and GGUF](15-llama-cpp-gguf/) | Verify official GGUF checksums, build pinned llama.cpp CPU/CUDA images, serve locally, and compare quantization/offload |
| [16 — Engine shootout capstone](16-capstone-engine-shootout/) | Produce a strict repeated four-engine comparison and an evidence-backed architecture decision record |

The common contract is:

```text
source model: Qwen/Qwen2.5-0.5B-Instruct
revision:     7ae557604adf67be50417f59c2c2f167def9a775
served alias: course-model
API:          /v1/chat/completions
results:      oms-benchmark/v1
exposure:     ClusterIP or loopback only
```

Lesson 15's Q4 GGUF treatment is explicitly a mixed runtime/artifact comparison,
not an exact FP16 scheduler comparison.
