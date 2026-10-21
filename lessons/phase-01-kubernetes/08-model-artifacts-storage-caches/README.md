# 08 — Model artifacts, storage, and caches

**Status:** outline
**Time:** 4 hours
**Compute:** `g1`, approximately 60 GPU-minutes
**Prerequisites:** 06, 07

## Why this matters

Large weights should not be hidden inside mutable images, and cold-start behavior
depends on where artifacts are stored and cached.

## Learning outcomes

- Compare image layers, ephemeral storage, local NVMe, EBS, EFS, and S3.
- Pin model and tokenizer revisions.
- Measure cold and warm model startup.

## Under the hood

Trace artifact download, filesystem cache, memory mapping, host RAM, and GPU
loading. Explain persistence and failure semantics for each storage choice.

## Lab outline

1. Stage a pinned model outside the image.
2. Start the same workload from a cold and warm cache.
3. Delete/recreate the Pod and node.
4. Record which data survives.

## Evidence to collect

- Startup timeline
- Storage decision record
- Artifact provenance

## Completion gate

The learner chooses a storage path based on measured startup and durability
requirements.

## Cleanup

Remove temporary volumes/caches and verify retained artifacts are intentional.
