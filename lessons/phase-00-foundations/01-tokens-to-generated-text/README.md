# 01 — From tokens to generated text

**Status:** outline
**Time:** 3 hours
**Compute:** `local-cpu`
**Prerequisites:** 00

## Why this matters

Every later serving and training optimization changes some part of the same
token-to-token execution path.

## Learning outcomes

- Trace tokenization, model forward passes, logits, sampling, and decoding.
- Distinguish prefill from iterative decode.
- Explain temperature, top-k, top-p, stopping, and deterministic decoding.

## Under the hood

Implement the autoregressive loop explicitly and annotate tensor shapes from
token IDs through logits.

## Lab outline

1. Load a pinned tiny model and tokenizer.
2. Write a minimal greedy generation loop.
3. Add sampling and stop conditions.
4. Log timings for prefill and each decode iteration.

## Evidence to collect

- Generation trace
- Tensor-shape diagram
- Comparison of two sampling policies

## Completion gate

The learner can reproduce framework generation for a fixed seed and explain each
step without calling a high-level serving engine.

## Cleanup

Remove local model cache only if it was marked temporary.
