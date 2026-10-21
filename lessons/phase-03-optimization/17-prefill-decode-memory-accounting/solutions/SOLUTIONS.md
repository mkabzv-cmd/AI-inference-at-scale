# Lesson 17 exercise solutions

<details>
<summary>Why does GQA reduce KV memory but not the query projection?</summary>

Grouped-query attention keeps one query head per attention head, but several
query heads share each key/value head. The query tensor therefore still has
`num_attention_heads`, while cached K and V tensors use
`num_key_value_heads`. In the supplied model the ratio is `14 / 2 = 7`, so its
KV payload is one seventh of the same-width MHA design, all else equal.
</details>

<details>
<summary>Why is the safe simulated OOM better than allocating until CUDA fails?</summary>

It tests the arithmetic and the program's rejection behavior without risking
other workloads, allocator fragmentation, a wedged notebook, or paid GPU time.
The optional engine run is then used only to reconcile a safe boundary near the
observed capacity.
</details>

<details>
<summary>What should a prediction-versus-measurement discrepancy contain?</summary>

Keep the discrepancy. Record engine version and digest, model revision, total
and free memory before startup, engine-reported weight/KV allocation, peak
`nvidia-smi` memory, workload shape, and likely omitted terms. Do not “fix” the
calculator with a mystery fudge factor.
</details>
