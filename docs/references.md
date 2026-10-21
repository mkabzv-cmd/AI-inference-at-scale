# Primary Reference Pack

Pin exact versions in individual lessons. These links are starting points, not a
substitute for lesson-level validation.

## Kubernetes, EKS, and NVIDIA

- [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [NVIDIA Kubernetes device plugin](https://github.com/NVIDIA/k8s-device-plugin)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)
- [NVIDIA GPU telemetry and DCGM exporter](https://docs.nvidia.com/datacenter/cloud-native/gpu-telemetry/latest/dcgm-exporter.html)
- [EKS accelerated AMIs](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-ami.html)
- [EKS device management](https://docs.aws.amazon.com/eks/latest/userguide/device-management.html)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)

## Inference engines and optimization

- [Transformers LLM tutorial](https://huggingface.co/docs/transformers/llm_tutorial)
- [Transformers serving](https://huggingface.co/docs/transformers/main/serve-cli/serving_optims)
- [vLLM documentation](https://docs.vllm.ai/)
- [vLLM optimization guide](https://docs.vllm.ai/en/latest/configuration/optimization/)
- [SGLang documentation](https://docs.sglang.io/)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [TensorRT-LLM documentation](https://nvidia.github.io/TensorRT-LLM/latest/)

## Distributed systems

- [PyTorch distributed overview](https://docs.pytorch.org/tutorials/beginner/dist_overview.html)
- [PyTorch tensor parallel tutorial](https://docs.pytorch.org/tutorials/intermediate/TP_tutorial.html)
- [PyTorch pipeline parallel tutorial](https://docs.pytorch.org/tutorials/intermediate/pipelining_tutorial.html)
- [NCCL documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
- [NCCL tests](https://github.com/NVIDIA/nccl-tests)
- [KubeRay GPU guide](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/gpu.html)
- [vLLM pipeline parallelism with KubeRay](https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/pipeline-parallelism-kuberay.html)

## Fine-tuning and evaluation

- [TRL SFT Trainer](https://huggingface.co/docs/trl/en/sft_trainer)
- [PEFT LoRA guide](https://huggingface.co/docs/peft/en/developer_guides/lora)
- [Transformers bitsandbytes quantization](https://huggingface.co/docs/transformers/en/quantization/bitsandbytes)
- [PyTorch FSDP2](https://docs.pytorch.org/docs/main/distributed.fsdp.fully_shard.html)
- [DeepSpeed ZeRO](https://deepspeed.readthedocs.io/en/latest/zero3.html)
- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)

## Retrieval and operations

- [Sentence Transformers retrieve and rerank](https://sbert.net/examples/applications/information-retrieval/README.html)
- [FAISS](https://faiss.ai/)
- [OpenSearch vector search](https://docs.opensearch.org/latest/vector-search/)
- [MLflow tracking](https://mlflow.org/docs/latest/ml/tracking/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)

## Papers

- [LoRA](https://arxiv.org/abs/2106.09685)
- [QLoRA](https://arxiv.org/abs/2305.14314)
- [Direct Preference Optimization](https://arxiv.org/abs/2305.18290)
- [PagedAttention / vLLM](https://arxiv.org/abs/2309.06180)

Last broad review: 2026-10-21.
