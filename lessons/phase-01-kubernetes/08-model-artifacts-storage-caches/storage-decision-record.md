# Model storage decision record

## Status

Proposed / accepted / superseded

## Context

- Model ID:
- Immutable model revision:
- Declared license and review evidence:
- Integrity-verification method:
- Approximate artifact size:
- Expected replicas:
- Expected Pod replacements per day:
- Cold-start objective:
- Availability Zones:
- Read/write pattern:
- Regulatory or data-classification constraints:

## Decision

### Authoritative artifact source

State the system that owns the durable copy and how integrity is verified.

### Node/Pod cache

State the cache technology, key layout, invalidation rule, capacity limit, and
what happens when it disappears.

### Kubernetes objects

- StorageClass:
- CSI provisioner:
- PVC access mode:
- Requested capacity:
- Volume binding mode:
- Reclaim policy:

## Evidence

| Experiment | Result |
|---|---|
| Cold `emptyDir` | |
| New Pod with `emptyDir` | |
| Cold PVC | |
| New Pod with same PVC | |
| Optional GPU load | |

## Alternatives considered

### Weights in the application image

Why accepted or rejected:

### EFS shared filesystem

Why accepted or rejected:

### S3 plus local node cache

Why accepted or rejected:

### EBS per replica

Why accepted or rejected:

## Failure and recovery

- If a Pod is deleted:
- If a node is lost:
- If an Availability Zone is unavailable:
- If the model source is unavailable:
- If a cache contains a different revision:
- If the completion marker and file-size evidence disagree:

## Security and cost

- Encryption:
- AWS authorization:
- Network path:
- Secret handling:
- Orphan-volume detection:
- Budget alarm/tagging:

## Consequences

Describe the operational benefits, limits, and work this decision creates.
