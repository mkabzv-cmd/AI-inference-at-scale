# Operator runbook

## Identity and scope

- Project/environment/release: __REQUIRED__
- Supported topology and regions: __REQUIRED__
- Owners, escalation path, and change window: __REQUIRED__
- Data classification and approved callers: __REQUIRED__

## Deploy a private candidate

Record exact reviewed revision, immutable release path, GitOps pointer change,
reconciliation command, readiness check, and expected output: __REQUIRED__

## Verify access controls before content

Record commands and identifying responses for anonymous denial, authenticated
but unauthorized denial, and one authorized request: __REQUIRED__

## Observe

Record dashboard, log, trace, engine, GPU, Pod, and node queries. Include queue,
TTFT, inter-token latency, errors, KV cache, restarts, and ready capacity:
__REQUIRED__

## Diagnose and recover

Give exact steps for queue saturation, a stuck startup, one failed GPU worker,
metric loss, bad index/adapter compatibility, and a failed rollout:
__REQUIRED__

## Roll back

Name the known-good immutable release, pointer update, reconciliation check,
post-rollback smoke check, and access-denial recheck: __REQUIRED__

## Teardown

List scoped cleanup scripts, Kubernetes/cloud inventory commands, asynchronous
deletion checks, and the zero-residual acceptance condition: __REQUIRED__
