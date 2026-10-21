# Glossary

This is an initial glossary. Each published lesson should add terms it introduces.

- **Decode:** repeated generation of output tokens after prefill.
- **DP:** data parallelism; complete model replicas process different requests or
  batches.
- **EFA:** AWS network interface for low-latency, high-throughput distributed
  workloads.
- **EP:** expert parallelism; experts of a mixture-of-experts model are placed
  across ranks.
- **GPU worker:** process or Pod that owns one or more GPU devices and executes
  model work.
- **ITL/TPOT:** inter-token latency or time per output token.
- **KV cache:** attention keys and values retained for already processed tokens.
- **NCCL:** NVIDIA communication library for GPU collectives and point-to-point
  communication.
- **PP:** pipeline parallelism; transformer layers are divided into stages.
- **Prefill:** processing of input tokens before the first generated token.
- **RAG:** retrieval-augmented generation.
- **Rank:** numeric identity of a process in a distributed process group.
- **SFT:** supervised fine-tuning.
- **TP:** tensor parallelism; tensors and operations within layers are sharded.
- **TTFT:** time to first token.
- **World size:** total number of participating distributed processes.
