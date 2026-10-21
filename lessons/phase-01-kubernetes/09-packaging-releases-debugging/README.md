# 09 — Packaging, releases, and debugging

**Status:** outline
**Time:** 5 hours
**Compute:** `local-cpu`, optional `g1`
**Prerequisites:** 06–08

## Why this matters

Copied YAML drifts. A release package must expose deliberate configuration and
remain debuggable through the underlying Kubernetes objects.

## Learning outcomes

- Convert raw manifests into a small Helm chart.
- Use immutable images and explicit values.
- Diagnose CrashLoopBackOff, failed scheduling, and bad rollout state.
- Roll back a release.

## Under the hood

Render templates locally and map each generated object to its controller,
selector, configuration, and lifecycle.

## Lab outline

1. Package the model service.
2. Install two configurations.
3. Introduce command, resource, and probe failures.
4. Repair or roll back each release.

## Evidence to collect

- Rendered manifests
- Debugging decision tree
- Rollback transcript

## Completion gate

The chart is a reproducible configuration interface rather than an opaque YAML
generator.

## Cleanup

Uninstall releases, delete the namespace, and verify cloud resources.
