# 06 — Configuration, health, and request flow

**Status:** outline
**Time:** 4 hours
**Compute:** `local-cpu`
**Prerequisites:** 05

## Why this matters

Model servers load slowly, stream responses, and can be alive without being ready
to serve.

## Learning outcomes

- Use ConfigMaps and Secrets appropriately.
- Distinguish startup, readiness, and liveness probes.
- Trace client, Service, endpoint, Pod, and container ports.

## Under the hood

Follow DNS resolution and Service routing, then explain how probe state changes
endpoint membership and rollout behavior.

## Lab outline

1. Externalize configuration.
2. Add all three probe types.
3. Break each probe deliberately.
4. Trace a streaming HTTP request to the container.

## Evidence to collect

- Request-path diagram
- Probe transition timeline
- Diagnosis for each failure

## Completion gate

The learner can distinguish “running,” “ready,” and “reachable.”

## Cleanup

Remove lesson configuration, workloads, and namespace.
