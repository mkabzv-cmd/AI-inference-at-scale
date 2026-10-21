# 04 — Guided first inference on EKS

**Status:** outline
**Time:** 3 hours
**Compute:** `g1`, approximately 60 GPU-minutes
**Prerequisites:** 03 and AWS preflight

## Why this matters

An early end-to-end success gives every later Kubernetes concept a concrete
purpose.

## Learning outcomes

- Apply, inspect, and remove a namespaced GPU Pod.
- Request one GPU and confirm that the model uses it.
- Port-forward a private endpoint and stream a response.

## Under the hood

Follow the Pod from API submission through scheduling, image/model loading,
device allocation, readiness, request handling, and termination.

## Lab outline

1. Scale one lab GPU node.
2. Apply the provided tiny-model manifest.
3. Inspect events, logs, device assignment, and GPU memory.
4. Port-forward, generate text, and remove the workload.

## Evidence to collect

- Manifest and immutable inputs
- Response plus GPU evidence
- Cleanup verification

## Completion gate

The exact inference run can be reconstructed from the experiment record.

## Cleanup

Delete the namespace, verify no load balancer/PVC remains, and scale GPU desired
capacity to zero.
