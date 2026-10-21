# 32 — What training adds to the computation graph

**Status:** outline
**Time:** 5 hours
**Compute:** `local-cpu`, optional `g1`
**Prerequisites:** 23

## Why this matters

Training retains activations and adds gradients and optimizer state, making its
memory and communication profile fundamentally different from inference.

## Learning outcomes

- Explain forward, backward, optimizer, and scheduler steps.
- Account for parameters, gradients, optimizer state, master weights, and
  activations.
- Explain mixed precision and activation checkpointing.

## Under the hood

Differentiate automatic differentiation graphs from inference KV caches and
trace when tensors are created, retained, reduced, and freed.

## Lab outline

1. Implement a tiny causal-LM update.
2. Inspect gradients and optimizer state.
3. Predict and measure memory.
4. Enable checkpointing and explain the compute/memory exchange.

## Evidence to collect

- Tensor and computation graph
- Memory worksheet
- Measured trace

## Completion gate

The learner explains why a model that serves easily may not fully fine-tune on
the same GPU.

## Cleanup

Stop optional GPU work and remove temporary checkpoints.
