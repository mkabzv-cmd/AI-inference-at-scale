# Lesson 18 exercise solutions

<details>
<summary>Why can a larger token budget reduce drain time but worsen p95 TTFT?</summary>

More prompt tokens can be processed in one scheduler iteration, improving GPU
utilization and total work completed. If a large prefill consumes the iteration,
however, decode-ready or newly arrived requests wait longer. Throughput and tail
latency therefore move in different directions.
</details>

<details>
<summary>What problem does paging solve?</summary>

Paging lets a sequence's logical KV cache map to non-contiguous physical blocks.
The allocator can reuse blocks freed by completed sequences and does not need
one contiguous region sized for every sequence's maximum length. Paging does
not eliminate the partially used final block, metadata, or capacity limits.
</details>

<details>
<summary>How do you prove starvation rather than merely slow service?</summary>

Show arrivals, admissions, scheduler choices, resource occupancy, and the
victim's wait across many opportunities. A single slow request is not proof.
Then change only the fairness/admission rule and show the victim progresses
while the workload and capacity stay fixed.
</details>
