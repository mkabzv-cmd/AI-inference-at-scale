# Lesson 23 capstone report

## Executive decision

State the winning candidate, whether every gate passed, the objective value,
GPU-minute cost, and the largest known limitation.

## Immutable experiment contract

- Repository commit:
- Model ID/revision:
- vLLM tag/resolved digest/version:
- GPU/driver/CUDA:
- Kubernetes context and node type (sanitize before sharing):
- Workload file hash:
- SLO file hash:
- Total GPU-minutes:

## Baseline and candidates

| ID | Single changed mechanism(s) | Hypothesis | Outcome |
|---|---|---|---|

## Gate table

| Candidate | Success | Quality | TTFT p95 | E2E p95 | Output tok/s | Peak GiB | Feasible |
|---|---:|---:|---:|---:|---:|---:|---|

## Ablation and mechanism

Explain queueing, KV allocation, kernel/graph mode, prefix/cache behavior, and
why each accepted change affects the frozen workload.

## Repeatability

Include two clean winner runs and one close alternative. Report variance and
cache/warmup state.

## Failure drill

Show empty Service endpoints, failed behavioral request, selector repair, and
successful request after repair.

## Limitations, rollback, and cleanup

List generalization limits, rollback triggers/configuration, namespace deletion,
and GPU-node scale-down proof.
