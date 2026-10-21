# 43 — Grounded generation, RAG evaluation, and security

**Status:** outline
**Time:** 1 day
**Compute:** `g1`, approximately 120 GPU-minutes
**Prerequisites:** 41, 42

## Why this matters

Good retrieval does not guarantee faithful answers, and retrieved documents are
untrusted input that can carry prompt injection.

## Learning outcomes

- Assemble, order, deduplicate, and budget retrieved context.
- Produce citations and abstain when evidence is insufficient.
- Separate retrieval misses from generation failures.
- Test indirect prompt injection and access-control mistakes.

## Under the hood

Trace source spans into prompt context, generated claims, citation mapping, and
evaluation labels.

## Lab outline

1. Add grounded prompting and source citations.
2. Build answer and faithfulness checks.
3. Inject malicious or misleading documents.
4. Verify metadata/tenant filtering and safe failure.

## Evidence to collect

- Claim-to-source mappings
- Retrieval and answer metrics
- Adversarial test results

## Completion gate

The service cites evidence, abstains appropriately, and rejects cross-tenant or
malicious retrieval paths.

## Cleanup

Remove test documents, indexes, and model service resources.
