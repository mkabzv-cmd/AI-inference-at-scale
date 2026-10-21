# 41 — Ingestion, chunks, embeddings, and indexes

**Status:** outline
**Time:** 6 hours
**Compute:** `local-cpu`, optional `g1` for embeddings
**Prerequisites:** 40

## Why this matters

Retrieval quality begins with traceable ingestion and chunk identities, not with
the generation prompt.

## Learning outcomes

- Build idempotent parsing, normalization, chunking, and metadata pipelines.
- Explain embedding normalization and cosine, dot-product, and L2 search.
- Compare exact search with approximate-nearest-neighbor indexing.

## Under the hood

Trace each source document to versioned chunks, embeddings, index records,
metadata, and access-control attributes.

## Lab outline

1. Create a small versioned corpus.
2. Compare token-, sentence-, and section-aware chunking.
3. Implement brute-force semantic search.
4. Add an ANN vector index and measure recall/latency.

## Evidence to collect

- Source-to-chunk lineage
- Chunk statistics
- Exact-versus-ANN results

## Completion gate

Every retrieved chunk can be traced to its source/version and filtered by
metadata.

## Cleanup

Remove temporary indexes and any generated embeddings not intended for retention.
