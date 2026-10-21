# 47 — Security and governance

**Status:** outline
**Time:** 1 day
**Compute:** `local-cpu`, brief deployed-system verification
**Prerequisites:** 44–46

## Why this matters

Open-model platforms combine software, model, data, registry, retrieval, API, and
cloud trust boundaries.

## Learning outcomes

- Threat-model weights, datasets, adapters, images, APIs, caches, and retrieval.
- Use workload identity, least privilege, secrets, network controls, and tenant
  isolation.
- Verify model/data licenses, hashes, provenance, and safe artifact formats.

## Under the hood

Trace identities and data through every component and identify where untrusted
code/content can execute or escape its intended boundary.

## Lab outline

1. Produce a data-flow diagram and threat register.
2. Remove static credentials.
3. Restrict network and retrieval paths.
4. Tamper with an artifact and make validation reject it.

## Evidence to collect

- Threat model
- Identity/network policy
- Provenance and tamper-test results

## Completion gate

Residual risks are explicit and every permitted path has an identified principal
and purpose.

## Cleanup

Remove temporary credentials, policies, test tenants, and malicious fixtures.
