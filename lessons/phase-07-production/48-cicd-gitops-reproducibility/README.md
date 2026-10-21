# 48 — CI/CD, GitOps, and reproducibility

**Status:** outline
**Time:** 1–2 days
**Compute:** CPU CI plus bounded `g1` smoke test
**Prerequisites:** 45–47

## Why this matters

Model platforms must promote a compatible set of code, image, model, tokenizer,
adapter, index, configuration, and evaluation results.

## Learning outcomes

- Validate code, Helm output, schemas, policies, and artifact metadata.
- Build immutable releases and detect drift.
- Run smoke/regression gates before promotion.
- Perform canary rollout and rollback.

## Under the hood

Trace an approved source revision into image digest, model release contract,
rendered Kubernetes state, runtime verification, and deployment alias.

## Lab outline

1. Build non-GPU CI checks.
2. Publish a pinned test image/artifact manifest.
3. Deploy an ephemeral environment and run smoke tests.
4. Promote, introduce a regression, and roll back.

## Evidence to collect

- Pipeline definition
- Release manifest
- Gate and rollback results

## Completion gate

The same Git revision creates the same release contract and failed gates block
promotion.

## Cleanup

Destroy the ephemeral environment and all temporary registry/artifact versions
not intentionally retained.
