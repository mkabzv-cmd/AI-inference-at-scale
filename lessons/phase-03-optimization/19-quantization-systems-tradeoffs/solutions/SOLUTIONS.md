# Lesson 19 exercise solutions

<details>
<summary>Why can smaller groups improve quality but reduce compression?</summary>

Each group gets a scale fitted to a narrower value range, so one outlier affects
fewer ordinary weights. More groups require more scales (and sometimes zero
points), increasing metadata and scale loads. The best group size is therefore
an accuracy, storage, and kernel-layout decision.
</details>

<details>
<summary>Why can a 4-bit model be slower than FP16?</summary>

The hardware or engine may lack a fast kernel for that exact format and shape.
It may unpack/dequantize into a wider type, execute many small operations, or
fall back to a generic path. Lower storage reduces one cost; it does not
guarantee lower end-to-end execution time.
</details>

<details>
<summary>How should a real quality gate differ from the toy gate?</summary>

Use application inputs, the exact tokenizer/chat template, deterministic
sampling where possible, reviewed references or rubric, enough examples for
uncertainty, and failure slices. Compare outputs—not only perplexity or tensor
error—and freeze the gate before measuring performance.
</details>
