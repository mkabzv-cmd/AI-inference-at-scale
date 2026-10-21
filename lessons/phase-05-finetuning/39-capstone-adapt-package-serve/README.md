# 39 — Capstone: adapt, package, and serve

**Status:** outline
**Time:** 2–3 days
**Compute:** `g1`; optional `g3` training study
**Prerequisites:** 32–38; lesson 38 may be optional

## Why this matters

Fine-tuning is incomplete until the resulting artifact can be evaluated,
packaged, served, benchmarked, and rolled back.

## Learning outcomes

- Choose full, LoRA, or QLoRA adaptation for a task.
- Maintain tokenizer/config integrity and artifact provenance.
- Serve merged or unmerged adapters and compare with the base model.

## Under the hood

Trace base weights, adapter application/merge, quantization order, model loading,
runtime memory, and request behavior.

## Lab outline

1. Train against the frozen evaluation contract.
2. Select and package the best checkpoint.
3. Write data/model cards.
4. Serve it using the Phase-2 engine.
5. Repeat the common benchmark and evaluation.

## Evidence to collect

- Dataset/model cards
- Exact training config and curves
- Adapter or merged artifact
- Base-versus-tuned quality/performance report

## Completion gate

The adapted model clears declared gates and can be reproduced and served by
another learner.

## Cleanup

Remove training and serving resources; retain only approved, versioned artifacts.
