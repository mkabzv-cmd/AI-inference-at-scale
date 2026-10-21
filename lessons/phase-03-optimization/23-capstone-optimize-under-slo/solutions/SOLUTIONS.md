# Lesson 23 capstone solutions

<details>
<summary>Why does the synthetic selector reject the fastest row?</summary>

Candidate `c2-prefix-cache` has the highest synthetic output throughput but a
0.96 success rate, below the frozen 0.99 floor. Hard correctness, reliability,
quality, memory, and latency gates run before objective ranking.
</details>

<details>
<summary>Why repeat the winner and a close alternative?</summary>

A single run can win because of noise, startup state, cache state, or transient
contention. Repetition tests stability. Repeating a close alternative shows
whether the decision survives uncertainty rather than merely reproducing the
winner in isolation.
</details>

<details>
<summary>What makes the capstone reproducible?</summary>

The repository commit, exact model commit, engine image digest, candidate
configuration, workload hash, prompt/sampling contract, hardware/driver,
warmup and measurement counts, raw per-request results, SLO gate, and cleanup
record. A screenshot of a dashboard is not enough.
</details>
