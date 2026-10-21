# 23 — Capstone: optimize under an SLO

**Status:** outline
**Time:** 1–3 days
**Compute:** `g1`, fixed budget required
**Prerequisites:** 17–22

## Why this matters

Real tuning balances latency, throughput, memory, quality, compatibility, and
operational risk rather than maximizing one number.

## Learning outcomes

- Translate an application workload into measurable objectives.
- Tune within a 24 GB GPU constraint.
- Defend a configuration with mechanisms and ablations.

## Under the hood

Explain the winning configuration through scheduler behavior, memory use,
kernels, caching, and workload shape.

## Lab outline

1. Freeze the workload, p95 target, and quality floor.
2. Establish the engine baseline.
3. Run a bounded tuning plan.
4. Repeat the winning result and one close alternative.

## Evidence to collect

- Raw results and traces
- Pareto frontier
- Configuration, ablations, and limitations

## Completion gate

The system meets the declared objective and another learner can reproduce why.

## Cleanup

Remove every benchmark deployment, temporary artifact, and GPU node.
