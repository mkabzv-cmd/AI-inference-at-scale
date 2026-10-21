# Lesson 21 report

## Immutable inputs

- Target model/revision:
- Draft model/revision or model-free method:
- Engine image digest:
- Workload/prompt-set hash:

## Workload distributions

Record shared-prefix length and frequency, prompt/output distributions,
concurrency, and whether isolation domains may share cache entries.

## Results

| Technique | Controlled baseline | Hit/acceptance metric | TTFT p95 | ITL p95 | req/s | Peak VRAM | Quality |
|---|---|---:|---:|---:|---:|---:|---:|

## Mechanism evidence

Trace cache keys/blocks/eviction, prefill chunks/scheduler interleaving, or
draft proposals/verification/rejection.

## Win, loss, and failure repair

For each technique, show one favorable and one unfavorable workload. Document
the deliberate failure, repair, and operational/security limitation.
