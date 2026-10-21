# Distributed-inference study report

## Abstract

State the question, topology, model, strategies, and result without overstating
scope.

## Hypothesis

List predictions recorded before experiments and what would falsify them.

## Immutable inputs

- study-spec SHA-256:
- model ID/revision/license review:
- image digest and reported software:
- max model length / max sequences / cache GiB:
- Kubernetes/Ray/NCCL versions:
- instance type and topology:
- workload SHA-256:

## Method

Describe warm-up, measured requests, concurrency, repetitions, order, correctness
gate, timing convention, and capacity window.

## Network baseline

Report message-size curves, selected transport, and limitations.

## Results

Include raw-run links and distributions. Do not show only the best run.

## Failure and recovery

Compare controller recovery, Ray resource recovery, and API recovery.

## Cost

State GPU-hours, current price input, included terms, and omitted terms.

## Recommendation

Tie the decision to model fit, workload, network, reliability, and cost.

## Limitations and threats to validity

Include sample size, node placement, client location, missing TTFT/TPOT, cache
state, and anything incomparable.

## Reproduction

List exact commands from clean capacity through verified cleanup.
