# 25 — Parallelism taxonomy and arithmetic

**Status:** draft
**Estimated time:** 5–7 hours
**Compute profile:** local CPU only
**Estimated GPU-minutes:** 0
**Estimated cloud cost:** none; this lesson exists to reject bad plans before
capacity is provisioned
**Prerequisites:** lessons 02, 17, 19, and 24
**Last validated:** 2026-10-21
**Validated with:** Python 3.9 unit tests and static JSON parsing; formulas are
planning estimates, not engine-specific memory or traffic guarantees

## Why this matters

“I have three GPUs” is not a parallelization plan. A valid plan also answers:

- Are the GPUs replicas, layer stages, or shards of the same matrix?
- Does `DP × TP × PP` equal the number of worker ranks?
- Can the model's hidden size and attention-head count be divided by TP?
- How many layers land on each pipeline stage?
- Do weights plus KV cache plus runtime overhead fit on every rank?
- Which tensors cross the ordinary node network, and how often?

Three separate one-GPU nodes are a useful but asymmetric topology. `PP=3` can
split almost any stack of transformer layers into three contiguous groups.
`TP=3` requires important tensor dimensions to support three-way sharding and
adds collectives within layers. `DP=3` creates three complete replicas, so it
improves request capacity only when the model already fits one GPU.

This lesson turns those statements into arithmetic. Its planner intentionally
labels estimates and rejected layouts. It will not say a model fits merely
because raw quantized weights fit.

## Learning outcomes

By the end, you can:

- distinguish data, tensor, pipeline, sequence/context, and expert parallelism;
- calculate `world_size = DP × TP × PP` for a simple hybrid layout;
- explain replica groups, tensor groups, and pipeline groups;
- check hidden-size, attention-head, KV-head, and vocabulary divisibility;
- derive balanced and uneven pipeline layer assignments;
- estimate raw per-rank weight and KV-cache bytes;
- explain which estimates omit allocator, kernel, graph, metadata, padding, and
  activation details;
- compare approximate TP collective payload with PP boundary payload;
- explain why three GPUs can be natural for PP and awkward for TP; and
- export a machine-readable decision before renting GPUs.

## What you will build

`src/layout_planner.py` reads a model description and a DP/TP/PP layout:

```text
model facts + workload assumptions + topology
                  |
                  v
          validation checks
          /               \
      invalid             valid
  reasons + exit 2   per-rank memory,
                     layer map, payload estimates
                  |
                  v
             results.json
```

You will compare six scenarios, including valid DP, valid PP, valid three-way
TP for a deliberately compatible shape, and invalid TP for common power-of-two
shapes.

## Files in this lesson

```text
25-parallelism-taxonomy-arithmetic/
├── README.md
├── inputs/
│   ├── models.json       # illustrative architecture facts and budgets
│   └── scenarios.json    # layouts to evaluate
├── src/
│   ├── layout_planner.py
│   └── run_scenarios.py
└── tests/
    └── test_layout_planner.py
```

No third-party dependency is required. Run commands from this lesson directory.

## Concepts and mental model

### Data parallelism

For inference, data parallelism normally means complete model replicas serving
different requests:

```text
request queue -> replica 0: full model
              -> replica 1: full model
              -> replica 2: full model
```

Each replica needs the whole model and its own KV cache. The replicas do not
need a per-layer all-reduce for independent inference requests. A router or
scheduler distributes work. Training DDP is different: replicas also
synchronize gradients.

### Tensor parallelism

Tensor parallelism divides matrices inside a layer. A simplified column-sharded
linear layer splits output features:

```text
X @ [W0 | W1 | W2] -> [Y0 | Y1 | Y2]
```

Another projection may need an all-reduce or reduce-scatter to combine partial
results. TP can make one layer's weights fit across devices, but communication
occurs repeatedly through the model. That is why ordinary inter-node networking
can dominate small decode steps.

### Pipeline parallelism

Pipeline parallelism assigns contiguous layer ranges:

```text
stage 0: embeddings + layers 0..9
          activation tensor ->
stage 1: layers 10..19
          activation tensor ->
stage 2: layers 20..29 + output
```

Weights are divided by stage. Activations cross stage boundaries. Multiple
microbatches can occupy different stages, but fill and drain periods leave
pipeline bubbles. In autoregressive decoding, token dependencies and engine
scheduling make the timeline more complicated than a training textbook
pipeline.

### Other dimensions

**Sequence/context parallelism** divides work along the token dimension and is
often combined with TP for long contexts. **Expert parallelism** distributes
Mixture-of-Experts experts and routes tokens, commonly creating all-to-all
traffic. They matter, but the executable planner focuses on DP/TP/PP so every
formula remains inspectable.

## Under the hood

For the simplified layout:

```text
world_size = DP × TP × PP
```

With six GPUs, `DP=2, TP=1, PP=3` means two replicas, each a three-stage
pipeline. With three GPUs, only factorizations of three are possible:

```text
3 × 1 × 1  (three replicas)
1 × 3 × 1  (three tensor shards)
1 × 1 × 3  (three pipeline stages)
```

### Divisibility

A basic TP implementation commonly requires:

```text
hidden_size % TP == 0
attention_heads % TP == 0
```

KV heads require implementation-specific handling. Some engines replicate KV
heads when TP exceeds the KV-head count; others impose stricter conditions.
This planner deliberately uses a strict rule unless
`allow_kv_head_replication` is true. A vocabulary can be padded in many
implementations, so the planner reports vocabulary padding rather than always
rejecting.

Three is awkward for a model with hidden size 4096 and 32 attention heads:
neither divides by three. It is valid for an illustrative hidden size 768,
12-head architecture. “TP=3 is supported by the engine” does not override model
shape constraints.

### Raw memory estimate

The planner computes:

```text
raw_weight_bytes = parameters × bytes_per_weight
average_weight_bytes_per_rank ≈ raw_weight_bytes / (TP × PP)
```

DP does not divide per-rank weight memory because every replica has the same
model. A simplified decoder KV cache is:

```text
2 × layers × concurrent_sequences × sequence_tokens
  × kv_heads × head_dim × kv_element_bytes
```

An average can hide the rank that actually runs out of memory. The fit screen
therefore scales average weight bytes by the largest PP layer-count imbalance
and computes KV bytes from the largest local layer count plus
`ceil(kv_heads / TP)` local KV heads. That ceiling matters when an engine
replicates KV heads: dividing total KV bytes by TP would be falsely optimistic.
The output preserves both average and conservative per-rank fields. Real
engines may shard embeddings, replicate, pad, page, preallocate, or quantize
cache differently, so this remains a screening estimate. Runtime overhead is
an explicit input rather than hidden optimism.

### Communication estimates

For a ring-style all-reduce, a common algorithmic byte model per rank is:

```text
2 × (TP - 1) / TP × message_bytes
```

The planner assumes two hidden-state-sized TP reductions per local layer per
token only to compare orders of magnitude. It is not a profiler and does not
know the engine's kernels or collectives.

A PP boundary sends a hidden activation:

```text
batch_tokens × hidden_size × activation_bytes
```

per stage transition. PP communicates less frequently than per-layer TP in this
simplified view, but pipeline imbalance and bubbles can still make it slow.

## Prerequisites and preflight

```bash
cd lessons/phase-04-distributed/25-parallelism-taxonomy-arithmetic
python3 --version
python3 -m json.tool inputs/models.json >/dev/null
python3 -m json.tool inputs/scenarios.json >/dev/null
python3 -m unittest discover -s tests -v
```

Use Python 3.9–3.12. The input models are teaching profiles, not promises about
a particular downloadable checkpoint. Before using a real model, retrieve its
exact revision's `config.json`, parameter count or tensor index, quantization
metadata, and engine compatibility. Record the revision, not only the model
name.

## Cost and safety

This lesson must not start cloud resources. If you find yourself scaling a node
group, stop: arithmetic comes first.

Treat fit as a safety gate:

1. reject invalid dimensions;
2. estimate raw weights and KV cache;
3. add measured quantization metadata and runtime overhead;
4. retain margin;
5. validate with a tiny profile;
6. then run a bounded GPU experiment.

Never use the planner's `fits_estimate=true` as proof that an engine will load.
It omits implementation-specific workspace and fragmentation unless you put
them into the overhead input.

## Predict before running

Write predictions:

1. Does DP=3 help a model that needs two GPUs just for weights?
2. Is hidden size 4096 divisible by TP=3?
3. How are 32 layers distributed across PP=3?
4. Which strategy sends communication inside many transformer layers?
5. If concurrency doubles, what happens to the simplified KV estimate?
6. Does 4-bit weight storage imply 4-bit activations or KV cache?

## Lab outline

1. Run unit tests for the formulas.
2. inspect the model and scenario inputs.
3. evaluate all layouts.
4. explain every rejection.
5. change one workload variable.
6. write an architecture decision from evidence.

## Step-by-step lab

### 1. Test the arithmetic

```bash
python3 -m unittest discover -s tests -v
```

Expected:

```text
test_invalid_world_size ... ok
test_pp_layer_balance ... ok
test_three_way_tp_rejection ... ok
test_valid_three_way_tp ... ok
```

These tests verify the code matches the stated formulas. They do not validate
the formulas against a particular engine.

### 2. Run one valid pipeline plan

```bash
mkdir -p artifacts
python3 src/layout_planner.py \
  --models inputs/models.json \
  --model illustrative-30-layer \
  --gpus 3 --dp 1 --tp 1 --pp 3 \
  --output artifacts/pp3.json
python3 -m json.tool artifacts/pp3.json
```

Important fields:

```text
valid: true
pipeline_layers: [[0, 9], [10, 19], [20, 29]]
world_size: 3
```

The exact memory numbers follow the illustrative inputs. Explain each unit:
bytes are converted to GiB using powers of 1024.

### 3. Prove an invalid layout fails early

```bash
set +e
python3 src/layout_planner.py \
  --models inputs/models.json \
  --model power-of-two-7b-shape \
  --gpus 3 --dp 1 --tp 3 --pp 1 \
  --output artifacts/invalid-tp3.json
status=$?
set -e
printf 'exit=%s (2 expected)\n' "$status"
python3 -m json.tool artifacts/invalid-tp3.json
```

Expected reasons include hidden size and attention heads not divisible by
three. The output is still written so rejected plans remain auditable.

### 4. Evaluate the scenario matrix

```bash
python3 src/run_scenarios.py \
  --models inputs/models.json \
  --scenarios inputs/scenarios.json \
  --output artifacts/scenarios.json
python3 -m json.tool artifacts/scenarios.json
```

The command itself succeeds because the matrix intentionally contains rejected
cases. Check each case's `expected_valid` against `valid`.

### 5. Inspect groups

For a six-rank `DP=2, TP=1, PP=3` extension, draw:

```text
replica 0 pipeline: ranks 0 -> 1 -> 2
replica 1 pipeline: ranks 3 -> 4 -> 5
```

Then answer: which ranks hold the same layer range? Those ranks are data
parallel counterparts even though independent inference does not require
gradient synchronization.

### 6. Controlled workload change

Copy the illustrative model entry into an ignored file and change only
`concurrent_sequences` from 1 to 8:

```bash
cp inputs/models.json artifacts/models-concurrency-8.json
python3 - <<'PY'
import json
from pathlib import Path

path = Path("artifacts/models-concurrency-8.json")
data = json.loads(path.read_text())
data["illustrative-30-layer"]["concurrent_sequences"] = 8
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
python3 src/layout_planner.py \
  --models artifacts/models-concurrency-8.json \
  --model illustrative-30-layer \
  --gpus 3 --dp 1 --tp 1 --pp 3 \
  --output artifacts/pp3-concurrency-8.json
```

Only KV memory should scale with this variable in the simplified model.

## Inspect what happened

Compare:

```bash
python3 - <<'PY'
import json
from pathlib import Path

for name in ("pp3.json", "pp3-concurrency-8.json"):
    d = json.loads((Path("artifacts") / name).read_text())
    print(
        name,
        d["memory"]["weight_gib_per_rank"],
        d["memory"]["kv_cache_gib_per_rank"],
        d["memory"]["estimated_total_gib_per_rank"],
    )
PY
```

Also inspect `checks` even when `valid=true`; warnings such as vocabulary
padding or uneven pipeline layers affect implementation and balance.

## Deliberate failure

Set `--gpus 3 --dp 2 --tp 1 --pp 1`. The factor product is two, not three:

```bash
set +e
python3 src/layout_planner.py \
  --models inputs/models.json \
  --model illustrative-30-layer \
  --gpus 3 --dp 2 --tp 1 --pp 1 \
  --output artifacts/world-size-failure.json
test "$?" -eq 2
set -e
```

Diagnosis: one GPU is unassigned by the topology. Repair either the GPU count
or the factors. Do not invent an implicit spare rank.

## Controlled experiment

Compare DP=3, TP=3, and PP=3 for the compatible small shape. Hold model,
concurrency, context, element sizes, and total GPU count fixed. The planner
shows:

- DP repeats full weights per rank;
- TP divides weights but estimates frequent collective payload;
- PP divides weights and estimates boundary payload plus stage imbalance.

This is a hypothesis generator. Lessons 27–30 measure the actual system.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 src/run_scenarios.py \
  --models inputs/models.json \
  --scenarios inputs/scenarios.json \
  --output artifacts/scenarios.json
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/scenarios.json").read_text())
assert d["correctness"]["passed"] is True
assert any(not item["valid"] for item in d["scenarios"])
assert any(item["layout"]["pp"] == 3 and item["valid"] for item in d["scenarios"])
print("scenario expectations: PASS")
PY
```

## Expected result

The power-of-two teaching shape rejects `TP=3`; the divisible small shape
accepts it. `PP=3` gives contiguous layer ranges and may differ by at most one
layer when the layer count is not divisible by three. DP=3 preserves full
per-rank weight memory. Generated floating-point values depend only on the
committed inputs and should be reproducible.

## Troubleshooting

| Symptom | Cause to test |
|---|---|
| missing model key | compare `--model` with JSON object keys |
| exit 2 with output file | expected invalid plan; read `reasons` |
| factor mismatch | calculate DP × TP × PP |
| fit seems too optimistic | review bytes/weight, KV dtype, overhead, reserve |
| TP rejected unexpectedly | inspect exact model revision's shape and engine rules |
| PP imbalance warning | calculate quotient and remainder of layers / stages |
| vocabulary warning | determine whether chosen engine pads or rejects shards |

## Evidence to collect

- `artifacts/pp3.json`
- `artifacts/invalid-tp3.json`
- `artifacts/scenarios.json`
- `artifacts/pp3-concurrency-8.json`
- `artifacts/decision.md` with chosen layout, rejected alternatives,
  assumptions, and validation plan

No account identifiers should appear. Model input values and revision evidence
for a real checkpoint belong in the decision record.

## Knowledge check

1. Why does DP not make an oversized model fit?
2. Why can PP=3 be valid when TP=3 is invalid?
3. Which dimensions need checking for TP, and why?
4. Why is raw 4-bit weight size not a load-time memory guarantee?
5. What does the ring all-reduce byte model leave out?
6. How can pipeline stage imbalance appear even with equal layer counts?

## Exercises

Guided: add a 31-layer model, run PP=3, and explain the `[11, 10, 10]` layer
counts.

Independent: extend the planner with an `ep` factor and a strict expert-count
divisibility check. Do not add an all-to-all traffic estimate until you can
state its tensor shape assumptions.

<details>
<summary>Solution outline</summary>

Use quotient/remainder: `31 // 3 = 10`, remainder 1, so the first stage gets one
extra layer. For EP, include `ep` in the world-size factor only if your chosen
parallel decomposition treats it as an independent axis; document that choice.
Reject `num_experts % ep != 0`.

</details>

## Completion gate

You pass when tests are green, every scenario expectation matches, you can
explain all rejection reasons without reading the code, and your decision file
separates estimate from measurement. You must identify a valid three-GPU PP
layout, an invalid three-GPU TP layout, a valid compatible TP layout, and the
GPU experiment that would falsify your recommendation.

## Cleanup

No cloud resources exist. The generated `artifacts/` directory is ignored.
Check that you did not accidentally start capacity:

```bash
git status --short
```

If you reused an AWS shell from another lesson, separately inspect that node
group and return it to its recorded baseline.

## Primary references

Required, reviewed 2026-10-21:

- [PyTorch tensor parallel overview](https://docs.pytorch.org/docs/stable/distributed.tensor.parallel.html)
- [PyTorch pipelining](https://docs.pytorch.org/docs/stable/distributed.pipelining.html)
- [Megatron-LM paper](https://arxiv.org/abs/1909.08053)
- [GPipe paper](https://arxiv.org/abs/1811.06965)
- [vLLM parallelism and scaling](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/)

Optional depth:

- [GShard paper](https://arxiv.org/abs/2006.16668)
- [Switch Transformers paper](https://arxiv.org/abs/2101.03961)
