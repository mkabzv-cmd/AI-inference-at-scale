# Architecture decision record

## Decision identity

- Project: __REQUIRED__
- Release: __REQUIRED__
- Date: __REQUIRED__
- Owners and reviewers: __REQUIRED__
- Status: __REQUIRED__

## Problem and constraints

Describe the user workload, data classification, quality target, SLO, budget,
GPU availability, operator skill, and deadline. State which constraints are
measured and which are assumptions.

## Options evaluated

Compare at least:

1. one-GPU serving;
2. three-node distributed serving;
3. a smaller or quantized model;
4. managed service or deferring the project.

For every option, record memory fit, communication, failure domain, throughput,
tail latency, quality, operating burden, security, and cost evidence.

## Decision

Selected topology, engine, model revision, precision/quantization, batching and
cache settings, optional adapter, optional RAG, and why: __REQUIRED__

## Rejected alternatives

Name each rejected alternative and the evidence that made it inferior for this
specific workload. Do not use “best” without a declared comparison boundary.

## Consequences and review trigger

Document new risks, operational duties, reversibility, and the measurement that
will trigger reconsideration: __REQUIRED__
