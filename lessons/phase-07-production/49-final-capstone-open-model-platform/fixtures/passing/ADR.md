# Fixture architecture decision

## Decision identity

- Project/release: `oms-fixture` / `oms-fixture-1`
- Date: 2026-10-21
- Status: accepted only for verifier testing

## Decision

Use a one-GPU-shaped, no-GPU synthetic fixture with a teaching engine, optional
adapter metadata, and optional RAG metadata. The values exercise all capstone
relationships without claiming that a model, GPU, cluster, benchmark, auth
gateway, or cloud teardown ran.

## Alternatives

A three-node fixture would exercise topology arithmetic but add no runtime
truth. A live engine would make the repository test depend on hardware and
credentials. Both are rejected for the checked-in deterministic path.

## Consequence

Passing this fixture proves verifier mechanics only. `--require-operator-run`
must reject it.
