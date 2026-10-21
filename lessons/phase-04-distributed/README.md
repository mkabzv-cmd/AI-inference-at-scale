# Phase 4 — Distributed inference

Learn ranks, collectives, Ray/KubeRay, and parallelism arithmetic before running
quantized models across three deliberately network-constrained G-series nodes.

These lessons are roadmap outlines, not runnable teaching material yet:

| Lesson | Planned outcome |
|---|---|
| [24 — Distributed-process fundamentals](24-distributed-process-fundamentals/) | Run small process-group programs and trace bytes between ranks |
| [25 — Parallelism arithmetic](25-parallelism-taxonomy-arithmetic/) | Plan memory, topology, and communication before allocating GPUs |
| [26 — Ray and KubeRay](26-ray-kuberay-orchestration/) | Prove multi-node actor placement and recovery behavior |
| [27 — NCCL characterization](27-nccl-network-characterization/) | Benchmark point-to-point and collective communication |
| [28 — Toy-model multi-node mechanics](28-toy-model-multinode-mechanics/) | Build a correct distributed smoke test and diagnose failures |
| [29 — Pipeline-parallel large model](29-pipeline-parallel-large-model/) | Run a quantized model across three one-GPU stages |
| [30 — TP vs PP vs DP](30-tensor-vs-pipeline-vs-data/) | Compare layouts under the same topology and workload |
| [31 — Distributed inference capstone](31-capstone-distributed-inference-study/) | Produce a research-style performance, failure, and cost study |
