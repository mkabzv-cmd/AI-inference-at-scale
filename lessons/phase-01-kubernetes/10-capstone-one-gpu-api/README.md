# 10 — Capstone: rebuild a one-GPU model API

**Status:** outline
**Time:** 1–2 days
**Compute:** `g1`, budget before starting
**Prerequisites:** 05–09

## Why this matters

The learner should now be able to rebuild the first success without a provided
walkthrough.

## Learning outcomes

- Design and deploy a private OpenAI-compatible model endpoint.
- Combine GPU scheduling, storage, probes, networking, packaging, and debugging.
- Write an operational runbook.

## Under the hood

Document the complete lifecycle from desired capacity and scheduling through
model load, request streaming, termination, and node scale-down.

## Lab outline

1. Begin with a blank namespace.
2. Package and deploy the service.
3. Prove readiness and request correctness.
4. Delete a Pod and observe recovery.
5. Diagnose one instructor-supplied fault.

## Evidence to collect

- Source, chart, and pinned artifacts
- Runbook and architecture diagram
- Restart/failure evidence
- GPU-hour and cleanup report

## Completion gate

Another learner can deploy and operate the endpoint solely from the submitted
documentation.

## Cleanup

Run the capstone teardown and prove zero GPU nodes, load balancers, and temporary
volumes.
