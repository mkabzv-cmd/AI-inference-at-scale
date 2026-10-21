# ADR: knowledge and behavior adaptation strategy

## Status

Proposed

## Context

Describe the user task, knowledge sources, update frequency, required response
behavior, caller-specific access rules, latency/SLO, cost boundary, model
context limit, data sensitivity, and failure severity.

## Options considered

- Prompting only
- Long context
- Retrieval-augmented generation
- Fine-tuning
- RAG plus fine-tuning

For every option, record feasibility, prototype evidence, update path,
provenance/citation behavior, operational components, evaluation plan, and
failure modes.

## Decision

Name the selected option and the exact assumptions that make it preferable.
Reference `artifacts/decisions.json`, but do not use its score as the sole
reason.

## Consequences

List new services, indexes, training artifacts, security boundaries, latency,
cost, ownership, monitoring, rollback, and deletion requirements.

## Validation and reversal

Define the smallest prototype, acceptance metrics, dates, owner, and evidence
that would reverse this decision.
