# 26 — Ray and KubeRay orchestration

**Status:** outline
**Time:** 6 hours
**Compute:** `g3`, approximately 120 GPU-minutes
**Prerequisites:** 07, 24

## Why this matters

Multi-node engines need resource discovery, process placement, startup
coordination, service lifecycle, and failure handling.

## Learning outcomes

- Explain Ray head, workers, actors, resources, and placement groups.
- Read RayCluster/RayService objects and their generated Pods/Services.
- Place exactly one GPU participant on each G-series node.

## Under the hood

Trace Kubernetes scheduling, Ray registration, logical GPU advertisement,
placement-bundle allocation, and engine-rank startup. Distinguish a generic Ray
cluster, whose head can remain CPU-only, from the current vLLM Production Stack
pipeline-parallel pattern, whose GPU-visible head participates in model execution.

## Lab outline

1. Install a pinned KubeRay operator.
2. Run a trivial GPU actor on each node.
3. Verify one-pod-per-node placement.
4. Compare generic and vLLM-specific head/worker resource layouts.
5. Create and diagnose an impossible placement group.

## Evidence to collect

- Resource/actor map
- Kubernetes and Ray status
- Placement-failure diagnosis

## Completion gate

The learner explains both Kubernetes and Ray scheduling decisions.

## Cleanup

Delete Ray resources/operator if lesson-scoped and scale all GPU nodes to zero.
