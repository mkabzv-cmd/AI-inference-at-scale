# Curriculum Roadmap

Most ordinary lessons are designed for 2–4 hours. Capstones may take 1–3 days.
The pace is intentionally flexible; two lessons per week plus a capstone week at
each phase boundary produces a six-to-eight-month part-time path.

## Phase 0 — Foundations and first GPU success

| ID | Lesson | Primary output |
|---:|---|---|
| 00 | Course map, reproducibility, and cost safety | Environment record and verified zero-GPU cleanup |
| 01 | From tokens to generated text | Minimal autoregressive generation loop and trace |
| 02 | GPU systems for LLMs | Memory estimator and compute/memory microbenchmark report |
| 03 | Containers and the CUDA contract | Reproducible GPU image and compatibility diagnosis |
| 04 | Guided first inference on EKS | Pinned model response, GPU evidence, and cleanup proof |

**Phase gate:** reproduce one inference run with exact image, model, prompt,
sampling configuration, GPU-memory peak, output, and cleanup evidence.

## Phase 1 — Kubernetes and EKS

| ID | Lesson | Primary output |
|---:|---|---|
| 05 | Kubernetes objects and reconciliation | Ownership diagram and self-healing workload |
| 06 | Configuration, health, and request flow | Probed service and request-path trace |
| 07 | Resources and GPU scheduling | Intentionally placed GPU pod and Pending diagnosis |
| 08 | Model artifacts, storage, and caches | Cold/warm startup comparison and storage decision |
| 09 | Packaging, releases, and debugging | Helm package, broken-release diagnosis, and rollback |
| 10 | Capstone: rebuild a one-GPU model API | Endpoint, runbook, restart recovery, and zero-cost cleanup |

**Phase gate:** diagnose Pending, crashing, unready, and unreachable workloads
from Kubernetes evidence without copying the walkthrough.

## Phase 2 — Single-GPU inference engines

| ID | Lesson | Primary output |
|---:|---|---|
| 11 | Transparent Transformers baseline | Readable reference server and request profile |
| 12 | Benchmarking without lying to yourself | Shared workload definition, JSON schema, and baseline report |
| 13 | vLLM on one GPU | vLLM deployment and engine-metric interpretation |
| 14 | SGLang on one GPU | Equivalent service and scheduler/cache comparison |
| 15 | llama.cpp and GGUF | Quantization/offload experiment |
| 16 | Capstone: controlled engine shootout | Reproducibility bundle and engine decision record |

**Phase gate:** compare engines with the same workload, explain differences, and
include a correctness or quality check.

## Phase 3 — Inference optimization internals

| ID | Lesson | Primary output |
|---:|---|---|
| 17 | Prefill, decode, and memory accounting | Predicted-versus-observed VRAM report |
| 18 | Batching, scheduling, and paged attention | Queue/KV-block experiment |
| 19 | Quantization as a systems trade-off | Memory/performance/quality comparison |
| 20 | Attention kernels, compilation, and CUDA graphs | Profiler trace and launch/data-movement analysis |
| 21 | Prefix reuse, chunked prefill, and speculative decoding | Workloads that demonstrate wins and regressions |
| 22 | A disciplined tuning workflow | Evidence-backed diagnosis of supplied pathologies |
| 23 | Capstone: optimize under an SLO | Winning configuration, ablations, and limitations |

**Phase gate:** every claimed optimization has a mechanism, controlled
measurement, quality gate, and documented downside.

## Phase 4 — Distributed inference on G-series nodes

| ID | Lesson | Primary output |
|---:|---|---|
| 24 | Distributed-process fundamentals | Small `torch.distributed` programs and byte traces |
| 25 | Parallelism taxonomy and arithmetic | Topology/memory/communication planner |
| 26 | Ray and KubeRay orchestration | Multi-node GPU actor placement proof |
| 27 | Characterize the network with NCCL | Point-to-point and collective benchmark report |
| 28 | Multi-node mechanics with a toy model | Correct TP smoke test and failure diagnoses |
| 29 | Pipeline-parallel large-model inference | Quantized model running with `TP=1, PP=3` |
| 30 | Tensor vs pipeline vs data parallelism | Comparable network, latency, and throughput results |
| 31 | Capstone: distributed-inference study | Research-style report, failure drill, and cost analysis |

**Phase gate:** explain why a parallel layout fits the model and topology before
launching it, then validate the prediction with network and engine evidence.

## Phase 5 — Fine-tuning and serving the result

| ID | Lesson | Primary output |
|---:|---|---|
| 32 | What training adds to the computation graph | Training-memory derivation and measured trace |
| 33 | Dataset engineering and chat templates | Versioned dataset plus data card |
| 34 | Evaluation before optimization | Frozen acceptance set and base-model results |
| 35 | Single-GPU supervised fine-tuning | Resumable SFT run and learning curves |
| 36 | LoRA and QLoRA from the matrix math | Adapter experiments and VRAM/quality report |
| 37 | Training-performance controls | Profile-driven training configuration |
| 38 | Distributed training: DDP, FSDP2, and ZeRO | Memory/communication comparison across G-series nodes |
| 39 | Capstone: adapt, package, and serve | Evaluated adapter or merged model served through an engine |

**Phase gate:** no trained artifact is accepted without data/model cards,
immutable evaluation, exact configuration, and a served comparison with the
base model.

## Phase 6 — Retrieval-augmented generation

| ID | Lesson | Primary output |
|---:|---|---|
| 40 | RAG vs fine-tuning vs long context | Architecture decision for the course domain |
| 41 | Ingestion, chunks, embeddings, and indexes | Traceable corpus and exact/ANN retrieval comparison |
| 42 | Sparse, dense, hybrid retrieval, and reranking | Retrieval benchmark with recall/ranking metrics |
| 43 | Grounded generation, RAG evaluation, and security | Cited answers, abstention, and adversarial tests |
| 44 | Capstone: deploy the knowledge system | Base/tuned/RAG/tuned+RAG comparison |

**Phase gate:** retrieval and generation are evaluated separately, every answer
can expose its evidence, and access-control metadata survives ingestion.

## Phase 7 — Production and LLMOps

| ID | Lesson | Primary output |
|---:|---|---|
| 45 | Observability, load, and capacity | Dashboards, traces, and saturation report |
| 46 | Autoscaling and reliability | Demand-driven scaling, failure drill, and rollback |
| 47 | Security and governance | Threat model, least-privilege deployment, and provenance report |
| 48 | CI/CD, GitOps, and reproducibility | Validated promotion and rollback pipeline |
| 49 | Final capstone: open-model platform | Reproducible, evaluated, observable, secure platform |

**Final gate:** another person can deploy the system from Git, reproduce the
published results, observe it, recover it, and remove every billable resource.

## Optional electives

- TensorRT-LLM using its current PyTorch backend and high-level serving APIs.
- Four-GPU hybrid `TP=2, PP=2`.
- EFA networking and comparison with ordinary G-series Ethernet.
- Mixture-of-experts and expert parallelism.
- Disaggregated prefill/decode.
- Multi-LoRA serving and adapter routing.
- Multimodal serving and batching.
- Preference optimization such as DPO.
- Multi-tenant scheduling, quotas, and chargeback.
