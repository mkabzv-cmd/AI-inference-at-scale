# Lesson 40 solution notes

## Daily policies

RAG wins because the fixture makes citations, daily updates, and per-request
filtering hard requirements. Long context is feasible but scores lower on the
operational assumptions for a repeating service; fine-tuning cannot satisfy the
hard provenance/update requirements.

## Stable output behavior

Fine-tuning wins because the task asks for learned behavior, stable low request
overhead, and no external knowledge. A prompt-only prototype should still be
tried before paying the training and evaluation cost.

## Three supplied documents

Long context wins for the fixture because the corpus is tiny, one-off, and a
persistent retrieval service would add unnecessary operational surface. If the
documents exceed reliable context capacity or the task repeats at scale, the
decision can change.

## Fresh knowledge plus learned format

RAG plus fine-tuning is the only fixture strategy satisfying both citations and
learned behavior. It is also the most operationally complex option. The ADR
must justify why prompting the format is insufficient before adding tuning.

## Important limitation

The capability numbers are authored assumptions. They make disagreement
visible; they are not industry constants. Replace them with prototype evidence,
SLO measurements, and risk review for a real system.
