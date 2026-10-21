# 33 — Dataset engineering and chat templates

**Status:** outline
**Time:** 6 hours
**Compute:** `local-cpu`
**Prerequisites:** 32

## Why this matters

Fine-tuning quality and safety depend more on data contracts and evaluation
discipline than on launching a training job.

## Learning outcomes

- Build text, prompt/completion, and conversational datasets.
- Apply chat templates and assistant-only loss masks.
- Create splits, deduplicate, detect leakage, and record provenance/licenses.

## Under the hood

Trace raw examples through normalization, templating, tokenization, labels,
packing, padding, and loss masking.

## Lab outline

1. Define a small domain task.
2. Create and lint versioned JSONL.
3. Plot token lengths and packing efficiency.
4. Run leakage and duplication checks.

## Evidence to collect

- Dataset manifest and fingerprint
- Data card
- Token-length/split report

## Completion gate

Every training token has a documented source, purpose, split, and loss-mask
behavior.

## Cleanup

Remove private/generated intermediate data not intended for publication.
