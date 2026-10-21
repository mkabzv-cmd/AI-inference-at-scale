# 07 — Resources and GPU scheduling

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 45 GPU-minutes
**Prerequisites:** 05

## Why this matters

GPU workloads remain Pending or land on the wrong nodes when resource requests
and scheduling constraints are poorly understood.

## Learning outcomes

- Explain requests, limits, extended resources, and `nvidia.com/gpu`.
- Use labels, taints, tolerations, affinity, and topology constraints.
- Diagnose a Pending GPU Pod from scheduler evidence.

## Under the hood

Trace how the device plugin advertises capacity and how scheduler predicates
filter candidate nodes.

## Lab outline

1. Verify advertised GPU resources.
2. Schedule exactly one GPU Pod on the intended node.
3. Intentionally create unschedulable configurations.
4. Prevent ordinary workloads from occupying GPU nodes.

## Evidence to collect

- Node allocatable output
- Scheduling events
- Placement and isolation policy

## Completion gate

The learner can explain every scheduler decision in the lab.

## Cleanup

Delete workloads and return the GPU node group to zero.
