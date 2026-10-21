# 40 — RAG vs fine-tuning vs long context

**Status:** outline
**Time:** 4 hours
**Compute:** `local-cpu`
**Prerequisites:** 34 or 39

## Why this matters

Fine-tuning changes behavior; retrieval supplies updateable knowledge. Long
context and prompting provide other trade-offs.

## Learning outcomes

- Decide among prompting, long context, RAG, fine-tuning, or combinations.
- Compare freshness, provenance, latency, privacy, maintenance, and failure modes.
- Define the knowledge-system capstone.

## Under the hood

Trace where information enters model weights, prompt tokens, retrieved context,
and adapter parameters, and how each path can fail.

## Lab outline

1. Classify a set of product requirements.
2. Identify behavior versus knowledge gaps.
3. Estimate update and evaluation costs.
4. Write an architecture decision.

## Evidence to collect

- Decision matrix
- Architecture record
- Initial capstone evaluation questions

## Completion gate

The learner can explain why RAG and fine-tuning are complementary rather than
interchangeable.

## Cleanup

No cloud resources are required.
