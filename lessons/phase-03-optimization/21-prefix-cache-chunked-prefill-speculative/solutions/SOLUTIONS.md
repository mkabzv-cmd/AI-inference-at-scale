# Lesson 21 exercise solutions

<details>
<summary>Why does tenant B miss even with identical token IDs?</summary>

The teaching key includes the tenant isolation domain. Reusing a cache entry
across mutually untrusted tenants can create timing or data-isolation risks.
Real deployments must understand the engine's cache-salt/isolation controls
rather than assuming textual equality is an acceptable security boundary.
</details>

<details>
<summary>When does chunked prefill help?</summary>

It helps when long prefills would otherwise occupy large scheduling steps and
delay decode-sensitive work. Chunks let the scheduler interleave prompt work
with decode. Tiny chunks can add scheduling/kernel overhead, and a lone request
with no competing decode may gain nothing.
</details>

<details>
<summary>Why does exact output not prove speculative decoding is faster?</summary>

Exactness is a correctness gate. Speed also depends on draft cost, acceptance
length, target verification efficiency, added memory, batch/concurrency, and
whether spare compute exists. A poor draft can add work while preserving the
same target distribution.
</details>
