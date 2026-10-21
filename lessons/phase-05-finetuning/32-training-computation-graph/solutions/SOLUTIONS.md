# Lesson 32 solution notes

## Why the optimizer owns more elements than the model

The bigram model has 16 trainable weights. Full training creates 16 gradient
elements. AdamW adds a first-moment and a second-moment value for every
trainable weight, so the script reports 32 optimizer-state elements. A mixed
precision implementation may additionally keep FP32 master weights.

## Why inference is different

Inference reads parameters and creates temporary activations. Autoregressive
serving usually retains a KV cache across decode steps, but it does not retain a
backward graph, parameter gradients, or optimizer moments. Training normally
does retain forward values needed by backward and adds gradients plus optimizer
state. This is why "the weights fit" does not imply "full training fits."

## What activation checkpointing changes

Checkpointing deliberately does not save selected forward activations. Backward
re-runs those forward regions to reconstruct what it needs. The memory-planning
fixture represents that choice by lowering retained activation elements while
leaving weights, gradients, master weights, and Adam states unchanged.

The exact reduction is model- and partition-dependent. The fixture is a
controlled arithmetic example, not a benchmark claim.

## Expected CPU verification

The exact floating-point values are deterministic for the recorded seed, but
the acceptance gate intentionally checks properties instead of copying a loss:

- final loss is less than half the initial loss;
- gradient elements equal trainable parameter elements;
- Adam state elements equal twice the trainable parameter elements;
- uncheckpointed training planning exceeds checkpointed training planning;
- both training cases exceed the inference planning case.
