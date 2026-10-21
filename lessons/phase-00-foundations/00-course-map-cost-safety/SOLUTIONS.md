# Lesson 00 solutions

## Predictions

1. No. Untracked files and uncommitted edits are outside a commit.
2. No. The Deployment controller creates a replacement through its ReplicaSet.
3. No. A node group's desired capacity is AWS infrastructure state.
4. `3 × 1 × 20 / 60 = 1 GPU-hour`.
5. Model commits and image digests are suitable public identifiers. Tokens never
   are. This public course also avoids committing account IDs.

## Exercises

1. `node-hours = 2 × 45 / 60 = 1.5`; `GPU-hours = 2 × 4 × 45 / 60 = 6`.
2. It omits the OS, driver, non-Python CUDA libraries, image layers, hardware,
   model/tokenizer bytes, workload, and command.
3. `server:v1` and model `main` are mutable. The digest and commit are immutable.
4. Replacement Pod, GPU node, load balancer, persistent volume/cloud disk,
   snapshot, registry image, model cache, or retained logs.
5. Good checks use pinned prompts/data and a declared metric or rubric before
   comparing optimizations.
