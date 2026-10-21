# 46 — Autoscaling and reliability

**Status:** outline
**Time:** 1–2 days
**Compute:** `g1` or `g3`, strict budget
**Prerequisites:** 45

## Why this matters

GPU services load slowly, queue requests, and may be interrupted; CPU-style
autoscaling based only on utilization is often misleading.

## Learning outcomes

- Select queue-, request-, latency-, or engine-aware scaling signals.
- Explain Pod scaling, node provisioning, warm pools, and scale-to-zero.
- Apply backpressure, disruption controls, graceful draining, and rollback.

## Under the hood

Trace demand from arrival metrics through autoscaler decisions, Pod scheduling,
node launch, model load, readiness, and request admission.

## Lab outline

1. Establish a saturation threshold.
2. Scale on a meaningful demand metric.
3. Inject pod/node failure and optional Spot interruption.
4. Demonstrate bounded degradation and recovery.

## Evidence to collect

- Scaling timeline
- Cold-start and queue metrics
- Failure/recovery and rollback report

## Completion gate

Scaling improves the declared SLO without uncontrolled cost or request loss.

## Cleanup

Disable the load source, remove autoscaling test resources, and verify zero GPU
capacity.
