# 35 — Single-GPU supervised fine-tuning

**Status:** outline
**Time:** 1 day
**Compute:** `g1`, bounded training budget
**Prerequisites:** 32–34

## Why this matters

A transparent SFT run teaches the complete training lifecycle before adapters and
distributed frameworks reduce the visible surface.

## Learning outcomes

- Explain sampler, collator, accumulation, clipping, scheduler, and checkpoints.
- Overfit a tiny sample as an end-to-end pipeline test.
- Run, interrupt, resume, and evaluate a bounded SFT experiment.

## Under the hood

Trace each batch through forward loss, scaled backward passes, optimizer update,
checkpoint state, and validation.

## Lab outline

1. Write or inspect a plain PyTorch training loop.
2. Overfit a tiny subset.
3. Train the tiny/small model on the full lab dataset.
4. Interrupt and resume from a checkpoint.

## Evidence to collect

- Exact config and seed
- Training/validation curves
- Resume proof and final evaluation

## Completion gate

The complete run is reproducible and beats or explains failure against the frozen
baseline.

## Cleanup

Stop training nodes and retain only intentional checkpoints/artifacts.
