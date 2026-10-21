# 13 — vLLM on one GPU

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 90 GPU-minutes
**Prerequisites:** 12

## Why this matters

vLLM provides the course's primary production-style view of scheduling, paged KV
memory, metrics, and later distributed execution.

## Learning outcomes

- Deploy the current vLLM engine and OpenAI-compatible API.
- Map key configuration fields to scheduler and memory behavior.
- Interpret runtime and request metrics.

## Under the hood

Trace API server, scheduler, workers, model runner, KV-cache allocation, prefill,
and decode iterations.

## Lab outline

1. Serve the same model used in lesson 11.
2. Replay the identical benchmark workload.
3. Inspect process layout, logs, and metrics.
4. Change one memory or scheduling control.

## Evidence to collect

- Engine configuration and version
- Comparable benchmark JSON
- Process/request lifecycle diagram

## Completion gate

Every measured difference from the baseline has a plausible engine mechanism.

## Cleanup

Delete the vLLM release and return GPU capacity to zero.
