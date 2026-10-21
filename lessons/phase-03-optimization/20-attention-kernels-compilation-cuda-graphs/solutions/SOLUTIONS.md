# Lesson 20 exercise solutions

<details>
<summary>Why is FlashAttention exact rather than an approximation?</summary>

It changes the order and tiling of the same attention calculation. Online
softmax keeps a running maximum, denominator, and weighted numerator, rescaling
old partial results when a larger maximum appears. Subject to floating-point
rounding, it produces standard attention without storing the full score matrix
in high-bandwidth memory.
</details>

<details>
<summary>What does CUDA Graph replay remove?</summary>

It primarily reduces repeated CPU-side launch and framework orchestration for a
captured sequence of GPU work. It does not make the kernels' mathematical work
disappear. Capture also needs stable addresses and compatible shapes/control
flow, and it reserves memory used by captured graphs.
</details>

<details>
<summary>Why are warmup iterations part of the experiment contract?</summary>

Compilation, autotuning, module loading, allocator growth, cache population,
and graph capture can dominate early requests. Mixing them with steady-state
samples changes the question. Report cold start separately; exclude a declared
warmup only from the steady-state statistic.
</details>
