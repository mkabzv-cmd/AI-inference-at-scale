# Phase 5 — Fine-tuning

This phase connects training mathematics, data contracts, evaluation, full SFT,
parameter-efficient adaptation, performance measurement, distributed sharding,
and serving. All eight lessons are detailed practical drafts. CPU-safe paths
teach and verify the essential mechanics; GPU and EKS paths are guarded and
honestly marked where live validation remains learner work.

Work through the phase in order. Lessons 33 and 34 create contracts that later
lessons must not silently rewrite:

```text
32 training graph and state memory
  -> 33 immutable dataset and assistant-loss mask
  -> 34 frozen acceptance set and base result
  -> 35 transparent SFT/checkpoint lifecycle
  -> 36 LoRA and QLoRA math/artifacts
  -> 37 controlled profiling and performance study
  -> 38 optional multi-node replication/sharding
  -> 39 package, serve, evaluate, benchmark, and roll back
```

| Lesson | Practical outcome | Required compute |
|---|---|---|
| [32 — Training computation graph](32-training-computation-graph/) | Derive forward/backward/optimizer state and validate memory arithmetic | local CPU |
| [33 — Dataset engineering](33-dataset-engineering-chat-templates/) | Build deterministic splits, render chats, audit assistant-only labels, and write a data card | local CPU |
| [34 — Evaluation first](34-evaluation-before-optimization/) | Freeze acceptance bytes, baseline mixed-quality fixtures, and enforce release gates | local CPU |
| [35 — Single-GPU SFT](35-single-gpu-sft/) | Prove accumulation/checkpoint/resume mechanics and optionally train pinned Qwen with a plain loop | local CPU; optional one GPU |
| [36 — LoRA and QLoRA](36-lora-qlora/) | Implement low-rank gradients/merge, plan targets/ranks, and optionally train/package a PEFT adapter | local CPU; optional one GPU |
| [37 — Training performance](37-training-performance-controls/) | Preserve optimizer semantics, capture profiles, reject confounds, and select a Pareto operating point | local CPU; optional one GPU |
| [38 — DDP, FSDP2, and ZeRO](38-ddp-fsdp2-zero/) | Prove DDP equivalence, distinguish replication from sharding, and optionally study three one-GPU nodes | local CPU; optional three GPUs |
| [39 — Adapt-and-serve capstone](39-capstone-adapt-package-serve/) | Build an immutable release with cards, private serving, frozen evaluation, common benchmark, and rollback | local CPU; optional one GPU |

The core training example remains intentionally tiny and synthetic. Passing the
labs proves course mechanisms, not broad model capability. A promoted capstone
must retain exact model/tokenizer/data/config hashes, raw evaluation responses,
resource measurements, private-by-default deployment, and verified cleanup.

Do not start the three-node lesson simply because three nodes exist. Use DDP
when replicas and throughput are the question; use FSDP2 or ZeRO when state
sharding is the question. Ordinary G-series nodes are valid learning hardware
even when network communication makes scaling inefficient. Record that result
instead of inventing a speedup.

Every GPU extension should begin with identity, region/context, starting
capacity, quota, price/time budget, immutable image/model revisions, and a
cleanup plan. Every extension should end by querying both Kubernetes and the
owning cloud APIs. A finished training process is not evidence that nodes,
volumes, snapshots, or registries stopped incurring cost.
