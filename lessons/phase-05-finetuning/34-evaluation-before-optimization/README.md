# 34 — Evaluation before optimization

**Status:** outline
**Time:** 5 hours
**Compute:** `local-cpu` and `g1`
**Prerequisites:** 33

## Why this matters

Without a frozen baseline and acceptance set, fine-tuning success becomes
subjective and regressions remain invisible.

## Learning outcomes

- Define intended use, failure taxonomy, slices, and acceptance thresholds.
- Combine deterministic task metrics with reviewed generative examples.
- Explain variance, seeds, contamination, and judge limitations.

## Under the hood

Trace evaluation inputs through tokenizer/chat template, decoding configuration,
metric computation, and aggregation.

## Lab outline

1. Freeze a held-out acceptance set.
2. Evaluate the base model.
3. Review errors by slice.
4. Define release gates before training.

## Evidence to collect

- Evaluation contract
- Base-model results
- Error taxonomy and thresholds

## Completion gate

The learner cannot change the acceptance set merely because a trained model fails
it.

## Cleanup

Stop inference resources and preserve only approved evaluation artifacts.
