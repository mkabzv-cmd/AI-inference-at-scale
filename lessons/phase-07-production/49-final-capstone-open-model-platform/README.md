# 49 — Final capstone: an open-model platform

**Status:** outline
**Time:** multi-week project
**Compute:** selected from `g1`, `g3`, or an approved advanced profile
**Prerequisites:** 00–48

## Why this matters

The final artifact should demonstrate an operable lifecycle rather than an
isolated model demo.

## Learning outcomes

- Synthesize serving, optimization, distribution, adaptation, retrieval, and
  operations.
- State trade-offs and rejected alternatives.
- Hand the system to another operator.

## Under the hood

Document the full lifecycle from source data and base weights through training,
evaluation, artifact promotion, deployment, requests, telemetry, failure, and
rollback.

## Lab outline

1. Define the domain, SLO, quality gates, security boundaries, and budget.
2. Fine-tune and register an adapter.
3. Deploy one- or multi-node inference plus optional RAG.
4. Load-test, canary, inject failure, and roll back.
5. Reproduce from a clean environment.

## Evidence to collect

- Architecture and threat model
- Data/model/release contracts
- Quality and performance reports
- Dashboards, SLOs, cost envelope, failure drill, and runbook

## Completion gate

Another person can deploy, validate, observe, recover, roll back, and completely
remove the platform using the repository.

## Cleanup

Run the final teardown, inventory every cloud resource, and prove that no
unintended billable capacity remains.
