# Lesson 19 report

## Artifact provenance

- Baseline model ID/revision:
- Quantized model ID/revision:
- Quantization method/configuration:
- Engine image tag/digest:
- Model-card license reviewed:

## Frozen workload and quality gate

Describe the application slice, tokenizer, sampling, metric, floor, and why the
gate was chosen before performance testing.

## Results

| Format | Disk GiB | Peak VRAM GiB | Startup s | TTFT p95 | tok/s | Quality | Kernel/path evidence |
|---|---:|---:|---:|---:|---:|---:|---|

Do not insert toy numeric results into the real-model table.

## Mechanism

Trace stored codes, scales/zero points, dequantization or fused kernel,
accumulation dtype, output, and KV-cache dtype.

## Failure and repair

Record an unsupported-format/kernel fallback or failed quality gate, its
evidence, and the repaired decision.

## Decision and limitations

Choose a format for a stated budget; do not claim a universal winner.
