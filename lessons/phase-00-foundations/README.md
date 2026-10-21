# Phase 0 — Foundations and first GPU success

Build the inference and GPU systems mental model, learn the container/CUDA
boundary, and complete one carefully guided GPU inference run.

All lessons in this phase are runnable drafts:

| Lesson | What you learn and run |
|---|---|
| [00 — Course map, cost, and safety](00-course-map-cost-safety/) | Reproducible experiment records, GPU-hour budgeting, cloud audits, and verified cleanup |
| [01 — From tokens to generated text](01-tokens-to-generated-text/) | A hand-written autoregressive loop, sampling controls, KV-cache tracing, and result checks |
| [02 — GPU systems for LLMs](02-gpu-systems-for-llms/) | Memory arithmetic, CPU/GPU measurement, OOM prediction, and bandwidth experiments |
| [03 — Containers and the CUDA contract](03-containers-cuda-contract/) | A real CUDA-aware image, host/container compatibility checks, and failure diagnosis |
| [04 — First inference on EKS](04-first-inference-on-eks/) | Build, push, schedule, call, inspect, and remove a one-GPU inference endpoint |

`draft` means the teaching text and practical files exist. Static CI does not
prove the container, GPU, or EKS paths; complete each lesson's preflight,
verification, and cleanup in your own lab environment.

Start at lesson 00 even if you already know transformers. Its cost, evidence, and
cleanup rules apply to every later cloud lab.
