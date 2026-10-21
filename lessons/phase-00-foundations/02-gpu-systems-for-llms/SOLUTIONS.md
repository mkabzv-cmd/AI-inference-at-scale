# Lesson 02 solutions

## Predictions

1. `13e9 × 2 / 1024^3 ≈ 24.214 GiB`.
2. No. Ten percent reserve leaves 21.6 GiB, less than the weights alone.
3. It doubles when all other terms remain fixed.
4. No. Decode shapes, cache reads, memory bandwidth, batching, and engine
   behavior differ from a large square matrix multiply.
5. No. Inspect `nvidia-smi topo -m` and official exact-instance documentation.

## Exercises

1. 70B raw weights:
   - FP16: `140e9 / 1024^3 ≈ 130.39 GiB`
   - INT8: `70e9 / 1024^3 ≈ 65.19 GiB`
   - 4-bit: `35e9 / 1024^3 ≈ 32.60 GiB`
   Quantization metadata and runtime overhead are additional.
2. `2 × 32 × 16 × 8192 × 8 × 128 × 2 = 17,179,869,184 bytes = 16 GiB`.
3. Each process has a separate address space and VRAM. Model partitioning needs
   a distributed algorithm, communication libraries, rendezvous, network
   transfers, synchronization, scheduling, and failure handling.
4. Add workspace bytes to subtotal and JSON, validate non-negative input, and
   add a verification case proving headroom decreases by that exact amount.
5. A strong answer cites the exact instance size and date, then separates
   advertised capability from observed `nvidia-smi` and network-device output.
