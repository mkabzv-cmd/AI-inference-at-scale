# Cost and Cleanup Safety

Cloud cleanup is part of correctness.

## Before every GPU lab

Record:

- instance type and count;
- purchase model;
- maximum planned runtime;
- expected GPU-hours;
- storage and load-balancer resources;
- the exact cleanup command.

Prefer short, bounded experiments. Keep GPU node groups at zero outside lab
windows.

## Default exposure

Early services must use `ClusterIP` and local port-forwarding. Do not create a
public load balancer simply to test an endpoint.

## Required teardown verification

A lesson is incomplete until the learner verifies:

- no lesson pods or jobs are running;
- desired GPU-node capacity is zero;
- no unintended load balancer exists;
- temporary persistent volumes and snapshots are removed or intentionally kept;
- model caches have an explicit retention decision.

## Spot guidance

Use On-Demand capacity while debugging orchestration so interruptions are not
confused with application failures. Introduce Spot only after checkpoints,
retries, graceful termination, and idempotent startup are understood.

## Public course guidance

Express estimates in GPU-minutes or GPU-hours rather than hard-coding dollar
prices that become stale. Provide a command or calculator procedure for obtaining
the learner's current regional price.
