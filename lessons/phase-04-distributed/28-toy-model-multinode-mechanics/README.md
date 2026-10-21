# 28 — Multi-node mechanics with a toy model

**Status:** outline
**Time:** 5 hours
**Compute:** `g3`, approximately 90 GPU-minutes
**Prerequisites:** 25–27

## Why this matters

A tiny model isolates rank discovery, engine compatibility, and sharding
correctness from memory pressure and long downloads.

## Learning outcomes

- Start a multi-node engine deterministically.
- Select a model whose dimensions support the chosen TP degree.
- Validate distributed output against a single-rank reference.

## Under the hood

Trace model partitioning, rank initialization, parameter loading, collectives,
and token synchronization.

## Lab outline

1. Choose a tiny TP-compatible model.
2. Run it on one rank and three ranks.
3. Compare numerical outputs.
4. Break divisibility, environment consistency, and rank discovery.

## Evidence to collect

- Single/distributed outputs
- Rank and shard map
- Three failure diagnoses

## Completion gate

Distributed mechanics work before a large checkpoint is introduced.

## Cleanup

Remove Ray/engine jobs, caches if temporary, and GPU nodes.
