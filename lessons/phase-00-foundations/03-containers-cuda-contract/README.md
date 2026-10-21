# 03 — Containers and the CUDA contract

**Status:** outline
**Time:** 4 hours
**Compute:** `g1` for the compatibility lab
**Prerequisites:** 00, 02

## Why this matters

A container packages user-space libraries, but it does not package the host GPU
driver or physical device.

## Learning outcomes

- Explain OCI image layers and immutable builds.
- Distinguish host driver, container CUDA runtime, framework, and GPU architecture.
- Diagnose a driver/runtime/library mismatch.

## Under the hood

Trace device exposure from the host through containerd, NVIDIA Container Toolkit,
the device plugin, environment variables, and `/dev/nvidia*`.

## Lab outline

1. Build a minimal GPU image.
2. Record host and container driver/runtime versions.
3. Run a CUDA/PyTorch smoke test.
4. Reproduce and repair one intentional incompatibility.

## Evidence to collect

- Image digest and build inputs
- Compatibility matrix
- Failure and repair notes

## Completion gate

The learner can explain why `nvidia-smi` may work while an engine still fails.

## Cleanup

Delete the test Pod/image tag if temporary and scale GPU capacity to zero.
