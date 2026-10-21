# 16 — Capstone: controlled engine shootout

**Status:** outline
**Time:** 1–2 days
**Compute:** `g1`, budget before starting
**Prerequisites:** 11–15

## Why this matters

Engine selection should be an evidence-backed workload decision, not a leaderboard
copy.

## Learning outcomes

- Design a fair multi-engine comparison.
- Normalize model, tokenizer, prompts, sampling, and workload semantics.
- Include latency, throughput, memory, correctness, operations, and compatibility.

## Under the hood

Explain how each runtime's scheduler, cache, kernels, process model, and artifact
format affect the measured behavior.

## Lab outline

1. Freeze the workload and acceptance checks.
2. Run Transformers, vLLM, SGLang, and llama.cpp.
3. Repeat anomalous results.
4. Write an architecture decision record.

## Evidence to collect

- Raw results and environment fingerprints
- Quality/correctness output
- Decision matrix and limitations

## Completion gate

Another person can reproduce the comparison and understand why the selected
engine fits the stated workload.

## Cleanup

Remove every engine deployment and scale GPU capacity to zero.
