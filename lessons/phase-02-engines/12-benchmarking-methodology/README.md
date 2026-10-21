# 12 — Benchmarking without lying to yourself

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 90 GPU-minutes
**Prerequisites:** 11

## Why this matters

Warmup, prompt shape, output length, concurrency, queueing, and quality can easily
reverse an apparent engine result.

## Learning outcomes

- Distinguish TTFT, TPOT/ITL, end-to-end latency, and throughput.
- Build reproducible open- and closed-loop workloads.
- Separate cold-start, warmup, steady-state, and saturation measurements.

## Under the hood

Relate request arrival, queue wait, prefill, decode iterations, streaming, and
client backpressure to observed metrics.

## Lab outline

1. Implement the shared benchmark result schema.
2. Generate fixed prompt/output distributions.
3. Run warmup and controlled concurrency sweeps.
4. Add a minimal correctness/quality gate.

## Evidence to collect

- Workload definition
- Raw JSON results
- p50/p95 latency and throughput report

## Completion gate

Repeating the benchmark produces materially equivalent results and identifies its
uncertainty.

## Cleanup

Stop load generators and model services; return GPU capacity to zero.
