# 22 — A disciplined tuning workflow

**Status:** outline
**Time:** 5 hours
**Compute:** `g1`, approximately 120 GPU-minutes
**Prerequisites:** 17–21

## Why this matters

Optimization flags interact. Random sweeps produce anecdotes unless hypotheses,
controls, and quality gates are explicit.

## Learning outcomes

- Classify compute, memory, scheduler, CPU, storage, and network bottlenecks.
- Choose an appropriate metric, trace, or profiler.
- Run one-variable experiments and controlled interaction studies.

## Under the hood

Build an evidence chain from symptom to metric to trace to mechanism to
configuration.

## Lab outline

1. Diagnose three supplied pathologies.
2. State a hypothesis before changing configuration.
3. Validate with an ablation.
4. Reject at least one misleading “improvement.”

## Evidence to collect

- Hypothesis log
- Ablation table
- Quality gate and diagnosis

## Completion gate

Every selected change has evidence; every rejected change has a documented reason.

## Cleanup

Remove experiments and return GPU capacity to zero.
