# Tooling Decisions

This file records the intended teaching role of major tools. Revalidate it before
each public release.

## Core serving engines

- **Transformers:** readable baseline and a bridge between model code and
  specialized engines.
- **vLLM:** primary production-style engine for scheduling, paged KV memory,
  optimization, metrics, and distributed serving.
- **SGLang:** comparison engine for cache-aware scheduling, structured
  generation, and alternative runtime design.
- **llama.cpp:** GGUF, quantization, memory mapping, portability, and CPU/GPU
  offload.

## Advanced serving

- **TensorRT-LLM:** optional NVIDIA-specific study. Teach its current PyTorch
  backend and high-level APIs, not obsolete checkpoint-conversion and
  `trtllm-build` flows.

## Distributed orchestration

- Begin with raw `torch.distributed` and Kubernetes primitives.
- Use Ray/KubeRay after ranks, rendezvous, collectives, Pods, Services, and
  scheduling are understood.
- Use Kubeflow Trainer or an equivalent operator only after a raw distributed
  training job has been built.

## Training

- PyTorch for the transparent training loop.
- Transformers/TRL for supervised and preference training workflows.
- PEFT for LoRA and related adapters.
- PyTorch FSDP2 and DeepSpeed ZeRO for sharding studies.

## Tools excluded from core new lessons

- Hugging Face TGI: legacy/archived path; its own project directs new users to
  alternatives.
- TorchServe: archived and unsuitable as a new course foundation.
- FasterTransformer: superseded by TensorRT-LLM.
- vLLM V0-specific tutorials and flags.
- `nvidia-docker`/`nvidia-docker2`: superseded by NVIDIA Container Toolkit.
- Kubernetes dockershim assumptions.
- EKS AL2 accelerated AMIs: use current AL2023 or Bottlerocket paths.
