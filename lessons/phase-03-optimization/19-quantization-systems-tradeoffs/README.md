# 19 — Quantization as a systems trade-off

**Status:** outline
**Time:** 6 hours
**Compute:** `g1`, approximately 150 GPU-minutes
**Prerequisites:** 17, 18

## Why this matters

Fewer bits reduce storage and memory, but conversion, kernel support, calibration,
and quality determine whether an application actually improves.

## Learning outcomes

- Explain floating-point and integer precision at a practical level.
- Distinguish weight-only, activation, and KV-cache quantization.
- Describe group scales, calibration, AWQ, GPTQ, and GGUF families.

## Under the hood

Trace quantized storage, scale lookup, dequantization, kernel execution, and
accumulation dtype.

## Lab outline

1. Select comparable full- and reduced-precision artifacts.
2. Measure memory, startup, TTFT, decode rate, and quality.
3. Identify kernel fallbacks.
4. Explain a case where fewer bits are not faster.

## Evidence to collect

- Precision matrix
- Quality/performance Pareto plot
- Kernel/compatibility notes

## Completion gate

The learner selects quantization from a quality and systems budget, not file size
alone.

## Cleanup

Remove temporary converted artifacts and scale GPU capacity to zero.
