# 42 — Sparse, dense, hybrid retrieval, and reranking

**Status:** outline
**Time:** 6 hours
**Compute:** `local-cpu`, optional `g1`
**Prerequisites:** 41

## Why this matters

Dense embeddings, lexical search, filters, fusion, and rerankers solve different
retrieval errors.

## Learning outcomes

- Compare BM25-style sparse and dense semantic retrieval.
- Build hybrid fusion and metadata filtering.
- Explain bi-encoder candidate generation and cross-encoder reranking.
- Measure recall@k, MRR, and nDCG.

## Under the hood

Follow query analysis, candidate retrieval, score normalization/fusion, reranking,
and top-k selection.

## Lab outline

1. Build a retrieval test set with relevant chunk IDs.
2. Compare sparse and dense baselines.
3. Add hybrid fusion and filters.
4. Rerank a wider candidate set.

## Evidence to collect

- Golden retrieval set
- Ranking metrics and latency
- Failure examples by query type

## Completion gate

Retrieval changes are accepted through component metrics before generation is
involved.

## Cleanup

Stop optional services and remove temporary indexes.
