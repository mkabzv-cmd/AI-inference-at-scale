# Phase 5 — Fine-tuning

Connect training mechanics, dataset engineering, evaluation, SFT, LoRA/QLoRA,
and distributed sharding back to serving and benchmarking.

These lessons are roadmap outlines, not runnable teaching material yet:

| Lesson | Planned outcome |
|---|---|
| [32 — Training computation graph](32-training-computation-graph/) | Derive and measure the memory added by gradients and optimizer state |
| [33 — Dataset engineering](33-dataset-engineering-chat-templates/) | Produce a versioned dataset and data card |
| [34 — Evaluation first](34-evaluation-before-optimization/) | Freeze acceptance data and measure the base model |
| [35 — Single-GPU SFT](35-single-gpu-sft/) | Run and resume supervised fine-tuning |
| [36 — LoRA and QLoRA](36-lora-qlora/) | Connect adapter matrix math to VRAM and quality measurements |
| [37 — Training performance](37-training-performance-controls/) | Tune from profiler evidence rather than folklore |
| [38 — DDP, FSDP2, and ZeRO](38-ddp-fsdp2-zero/) | Compare replication and sharding across G-series nodes |
| [39 — Adapt-and-serve capstone](39-capstone-adapt-package-serve/) | Package, evaluate, serve, and compare a tuned artifact |
