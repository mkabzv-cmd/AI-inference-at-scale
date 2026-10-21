# 44 — Capstone: deploy the knowledge system

**Status:** outline
**Time:** 2–3 days
**Compute:** `g1`, optional CPU retrieval services
**Prerequisites:** 39–43

## Why this matters

The system should demonstrate when base, tuned, RAG, and tuned+RAG approaches win
or fail on the same task.

## Learning outcomes

- Deploy ingestion, retrieval, reranking, and generation components.
- Scale and observe CPU/GPU boundaries independently.
- Compare knowledge freshness, quality, latency, and updateability.

## Under the hood

Trace one request end to end, including corpus/index version, candidates,
reranking, prompt construction, model execution, and citations.

## Lab outline

1. Freeze the corpus and evaluation set.
2. Deploy the full private service on Kubernetes.
3. Compare four system variants.
4. Update one source document and verify behavior.

## Evidence to collect

- Architecture and lineage diagrams
- Retrieval/answer/performance results
- Update and rollback procedure

## Completion gate

The selected architecture is justified by component-level and end-to-end
evidence.

## Cleanup

Delete model/retrieval services and temporary storage; verify retained corpus
artifacts are intentional.
