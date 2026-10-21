# Threat model

## Scope and assets

Project, environment, release, base weights, tokenizer, adapter, datasets,
corpus/index, prompts, responses, identities, telemetry, credentials, registry,
object storage, and availability requirements: __REQUIRED__

## Principals and trust boundaries

List human callers, workload identities, CI, GitOps, cluster controllers,
artifact publishers, data owners, operators, and every point where identity or
data classification changes: __REQUIRED__

## Threat register

| ID | Asset / boundary | Preconditions | Threat and impact | Prevent | Detect | Respond | Residual risk | Owner | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| T-01 | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ | __REQUIRED__ |

Include artifact substitution, unsafe deserialization, anonymous access,
cross-tenant retrieval, indirect prompt injection, sensitive logging, denial of
service, compromised CI, image/model drift, overprivileged workload identity,
GPU-node loss, incomplete deletion, and license/usage violations.

## Release boundary

State how anonymous and unauthorized denial are proved before restricted
content is attached, how authorization is tenant-scoped, and what forces a
fail-closed response: __REQUIRED__

## Review

Reviewers, date, accepted residual risks, expiry, and next review trigger:
__REQUIRED__
