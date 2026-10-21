# 00 — Course map, reproducibility, and cost safety

**Status:** outline
**Time:** 2 hours
**Compute:** `local-cpu`; brief cloud inspection, zero GPU-minutes
**Prerequisites:** basic Python, shell, and Git

## Why this matters

LLM experiments are useless when their inputs cannot be reconstructed, and cloud
labs become dangerous when cleanup is informal.

## Learning outcomes

- Describe the full course and its phase gates.
- Capture software, model, hardware, and workload fingerprints.
- Estimate GPU-hours before a lab and verify zero capacity afterward.

## Under the hood

Trace how mutable tags, model branches, environment state, and hidden defaults
turn an apparent benchmark into an irreproducible result.

## Lab outline

1. Run the environment preflight.
2. Create an experiment ID and metadata record.
3. Inspect the configured compute profile without launching it.
4. Practice the cleanup verification procedure.

## Evidence to collect

- Environment manifest
- Empty-cost baseline
- First experiment report

## Completion gate

Another learner can explain exactly what would run and prove that no GPU capacity
is active.

## Cleanup

No resources are created. Confirm the lab namespace is absent and GPU desired
capacity is zero.
