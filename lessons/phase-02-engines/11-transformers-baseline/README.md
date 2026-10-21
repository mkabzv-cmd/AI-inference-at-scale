# 11 — A transparent Transformers baseline

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 60 GPU-minutes
**Prerequisites:** 10

## Why this matters

A readable baseline reveals the work hidden by specialized serving engines.

## Learning outcomes

- Load a pinned model/tokenizer and apply its chat template correctly.
- Explain `generate`, KV-cache use, sampling, streaming, and cancellation.
- Identify the missing scheduler and memory-management capabilities.

## Under the hood

Trace one request through tokenization, prefill, decode, sampling, streaming, and
cleanup while recording tensor shapes and memory.

## Lab outline

1. Build a small FastAPI service around Transformers.
2. Add streaming and request cancellation.
3. Profile one cold and one warm request.
4. Record limitations under concurrent requests.

## Evidence to collect

- Source and pinned environment
- Request trace and profile
- Baseline limitations

## Completion gate

The learner can name precisely what a production engine must improve.

## Cleanup

Remove the deployment, cache as intended, and scale the GPU node group to zero.
