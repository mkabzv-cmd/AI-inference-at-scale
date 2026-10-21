# Lesson 20 report

## Reproducibility

- Engine image tag/digest:
- Model ID/revision:
- GPU/driver/CUDA:
- Attention backend reported by logs:
- Profiler and version:

## Frozen shapes

| Shape | Batch | Q tokens | KV tokens | Head dim | Why included |
|---|---:|---:|---:|---:|---|

## Cold start, warmup, and steady state

Keep compile/capture time separate from replay measurements.

## Evidence

| Mode | Kernel launches | Device time | CPU launch gaps | Peak VRAM | Correctness |
|---|---:|---:|---:|---:|---|

## Mechanism explanation

Point to operations fused, score-matrix traffic avoided, launch gaps removed,
and shapes that fell back or caused a new capture.

## Failure and repair

Record one dynamic-shape/fallback/compile problem, evidence, repair, and
remaining compatibility boundary.
