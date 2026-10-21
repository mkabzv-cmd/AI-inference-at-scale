# 36 — LoRA and QLoRA from the matrix math

**Status:** outline
**Time:** 1–2 days
**Compute:** `g1`, bounded training budget
**Prerequisites:** 35

## Why this matters

Parameter-efficient tuning makes useful model adaptation possible on affordable
GPUs, but rank, targets, scaling, and quantized bases still require judgment.

## Learning outcomes

- Derive the low-rank update and count trainable parameters.
- Explain rank, alpha/scaling, target modules, initialization, and merge behavior.
- Explain NF4, double quantization, frozen base weights, and QLoRA gradients.

## Under the hood

Implement a small `LoRALinear`, then map its parameters and gradients to PEFT and
the quantized base-model path.

## Lab outline

1. Compare manual and PEFT LoRA.
2. Sweep ranks and target modules.
3. Run a QLoRA experiment on a model that would not fully fine-tune.
4. Compare VRAM, speed, adapter size, and quality.

## Evidence to collect

- Parameter/memory accounting
- Adapter artifacts
- Quality and performance comparison

## Completion gate

The selected adapter design is justified by task evidence and resource limits.

## Cleanup

Return GPU capacity to zero and remove rejected checkpoints.
