# 45 — Observability, load, and capacity

**Status:** outline
**Time:** 1 day
**Compute:** `g1` or `g3` according to the selected system
**Prerequisites:** 23, 44

## Why this matters

Production behavior spans request queues, retrieval, schedulers, model phases,
GPU kernels, Kubernetes, and node capacity.

## Learning outcomes

- Correlate logs, metrics, and traces with a request ID.
- Observe TTFT, ITL, throughput, queue depth, KV use, and GPU/DCGM metrics.
- Build saturation curves and identify the first bottleneck.

## Under the hood

Trace a request across gateway, retrieval, engine scheduler, model runner, GPU,
and response stream.

## Lab outline

1. Add structured logs and distributed tracing.
2. Build service and GPU dashboards.
3. Run a step-load test.
4. Explain the first and second saturation points.

## Evidence to collect

- Dashboard and trace screenshots/exports
- Load-test results
- Capacity model

## Completion gate

An operator can diagnose high latency from evidence without entering a Pod first.

## Cleanup

Stop load, remove temporary telemetry data, and scale GPU capacity to zero.
