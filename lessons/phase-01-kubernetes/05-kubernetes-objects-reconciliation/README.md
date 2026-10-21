# 05 — Kubernetes objects and reconciliation

**Status:** outline
**Time:** 3 hours
**Compute:** `local-cpu` Kubernetes cluster
**Prerequisites:** 04

## Why this matters

Kubernetes manages desired state through controllers; it is not a remote shell
for long-lived servers.

## Learning outcomes

- Explain Pods, Deployments, ReplicaSets, Services, labels, and selectors.
- Distinguish desired from observed state.
- Read ownership and reconciliation evidence.

## Under the hood

Trace an object from API storage through controller reconciliation and scheduler
binding to kubelet execution.

## Lab outline

1. Run a CPU application as a Pod.
2. Replace it with a Deployment and Service.
3. Delete a managed Pod and observe recovery.
4. Break a selector and diagnose the result.

## Evidence to collect

- Object ownership diagram
- Events and status transitions
- Selector-failure diagnosis

## Completion gate

The learner predicts which controller recreates each deleted object.

## Cleanup

Delete the lesson namespace and verify no objects remain.
