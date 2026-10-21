# Phase 4 — Distributed inference

This practical block teaches distributed inference from first principles and
then applies those principles on three separate one-GPU Kubernetes nodes.
Ordinary G-series networking is an intentional constraint: the learner must
measure it, observe synchronization stalls, and decide which parallel strategy
is least harmed by it. No lesson assumes NVLink, InfiniBand, EFA, GPUDirect
RDMA, or multiple GPUs in one host.

The CPU paths are suitable for local development and correctness checks. The
GPU paths require an existing EKS lab node group that can provide exactly three
Ready one-GPU nodes. They do not create a VPC, EKS cluster, managed node group,
IAM role, or public endpoint.

| Lesson | Practical outcome |
|---|---|
| [24 — Distributed-process fundamentals](24-distributed-process-fundamentals/) | Run and break real `torch.distributed` collectives locally and on three nodes |
| [25 — Parallelism arithmetic](25-parallelism-taxonomy-arithmetic/) | Reject impossible DP/TP/PP layouts before spending GPU money |
| [26 — Ray and KubeRay](26-ray-kuberay-orchestration/) | Place one GPU actor per node and explain both schedulers |
| [27 — NCCL characterization](27-nccl-network-characterization/) | Measure latency/bandwidth and retain transport evidence |
| [28 — Toy-model multi-node mechanics](28-toy-model-multinode-mechanics/) | Validate sharded output against a single-process reference |
| [29 — Pipeline-parallel large model](29-pipeline-parallel-large-model/) | Deploy a digest-pinned `TP=1, PP=3` vLLM study profile |
| [30 — TP vs PP vs DP](30-tensor-vs-pipeline-vs-data/) | Compare strategies with one workload and honest feasibility labels |
| [31 — Distributed inference capstone](31-capstone-distributed-inference-study/) | Produce a reproducible performance, failure, and cost report |

## Shared safety helpers

The `common/` directory contains reusable EKS target assertions, bounded
three-node scaling, topology capture, namespace cleanup, and result-schema
validation. Read every script before running it. The scaling helper only accepts
an idle lab node group (`min=0`, `desired=0`) on first use, requires exact-name
confirmation, saves the original scaling configuration under the ignored
lesson `artifacts/` directory, and restores that exact configuration.

These are `draft` lessons. Static and CPU-safe paths are tested in this
repository. Multi-node GPU execution, image compatibility, model fit, network
performance, and Regional cost must be validated by the learner on the actual
cluster before any lesson can become `published`.
