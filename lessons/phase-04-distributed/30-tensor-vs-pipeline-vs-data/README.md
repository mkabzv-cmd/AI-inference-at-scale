# 30 — Tensor vs pipeline vs data parallelism

**Status:** outline
**Time:** 1 day
**Compute:** `g3`, fixed GPU-hour budget
**Prerequisites:** 25–29

## Why this matters

DP pools throughput, TP combines layer computation, and PP combines model stages;
they solve different problems and create different traffic.

## Learning outcomes

- Compare capacity scaling with throughput scaling.
- Identify per-layer collective traffic versus stage-boundary traffic.
- Explain why TP is especially sensitive to slow networks.

## Under the hood

Map identical requests through three replicas, a TP-compatible shard layout, and
a PP layout.

## Lab outline

1. Run three independent small-model replicas.
2. Run a valid two- or three-way TP experiment.
3. Run a comparable PP layout.
4. Compare network, TTFT, TPOT, throughput, and failures.

## Evidence to collect

- Common workload results
- Communication traces
- Architecture decision

## Completion gate

The learner chooses the strategy from model fit and workload, not merely the
number of GPUs.

## Cleanup

Remove all three layouts and verify zero GPU nodes.
