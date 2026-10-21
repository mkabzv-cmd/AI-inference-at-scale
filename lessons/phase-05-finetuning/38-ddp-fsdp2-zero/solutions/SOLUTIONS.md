# Lesson 38 solution notes

With equal local batch sizes and the same loss normalization, DDP's averaged
rank gradients equal the gradient of the concatenated global batch. DDP still
stores the full model and ordinary optimizer state on every rank. Adding two
more one-GPU nodes changes global throughput and batch construction, but does
not let a model larger than one GPU appear through automatic VRAM pooling.

The uneven-batch fixture is deliberately biased because it averages three rank
means equally although the ranks represent one, two, and three samples.
Production choices include a sampler that keeps valid sample counts equal,
loss scaling by actual sample/token counts, join semantics for exhausted
ranks, or a custom weighted reduction. Padding duplicate samples also changes
the data distribution and must be recorded.

ZeRO-1 shards optimizer state, ZeRO-2 additionally shards gradients, and
ZeRO-3 shards parameters as well. FSDP2 full sharding similarly materializes
needed parameters around module execution and reduce-scatters gradients. The
planner's division by world size is only state arithmetic: peak all-gathers,
activations, allocator fragmentation, communication buffers, and checkpoint
staging still determine whether a run actually fits.
