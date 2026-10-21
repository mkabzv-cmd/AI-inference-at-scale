# Lesson 22 exercise solutions

<details>
<summary>What is the first response to high TTFT?</summary>

Do not change a flag yet. Separate queue time from prefill and transport time.
High queue time with arrival rate above completion suggests saturation; high
prefill time with an empty queue suggests prompt/compute work; high client-only
time suggests the network or load generator. Each implies different evidence.
</details>

<details>
<summary>Why is the “fast” supplied run rejected?</summary>

It reduced mean output length from 96 to 24 and quality pass rate from 1.0 to
0.58. More requests per second is unsurprising when each request does less work.
It is not an optimization of the frozen workload.
</details>

<details>
<summary>When should an interaction study follow one-variable tests?</summary>

After each factor has a mechanism-backed reason to matter. Then test a small
factorial combination because scheduler, memory, and graph settings can
interact. Do not launch a blind combinatorial sweep whose winning sample cannot
be explained or reproduced.
</details>
