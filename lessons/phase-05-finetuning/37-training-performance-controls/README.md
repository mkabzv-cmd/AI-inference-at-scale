# 37 — Training-performance controls

**Status:** draft
**Time:** 6–10 hours
**Compute:** `local-cpu` for experiment design; optional `g1` for profiling and the controlled sweep
**GPU budget:** zero for the required path; estimate each candidate before enabling the optional sweep
**Prerequisites:** 35, 36
**Last reviewed:** 2026-10-21

## Why this matters

Training optimization is full of attractive but incomparable numbers. Increasing
microbatch size may raise GPU utilization while changing examples per update.
Shortening sequences may raise tokens per second while removing difficult long
examples. Packing may reduce padding while allowing cross-example attention if
the mask is wrong. Gradient checkpointing may lower memory while repeating
forward computation. An eight-bit optimizer may shrink state while changing
numerics and kernels. More data-loader workers may help, do nothing, or exhaust
host memory.

The problem is not finding a faster-looking log. It is preserving the learning
problem while changing one systems control, measuring enough steady-state
updates, and keeping quality and cost beside throughput.

This lesson gives you an experimental contract. The required CPU path validates
that all checked candidates expose the same number of token slots to every
optimizer update:

```text
token slots/update =
  microbatch × gradient accumulation × sequence length
```

It then exercises a Pareto analyzer on a file explicitly labeled as a synthetic
software fixture. Those numbers test the analyzer; they are not GPU benchmark
claims. A deliberate failure presents an apparently faster candidate that
secretly changed the dataset, run length, and token budget. The validator
rejects it.

The optional path materializes each treatment from lesson 35's real
Transformers loop. A separate script captures an actual `torch.profiler` trace.
You will report useful tokens, optimizer cadence, allocated and reserved VRAM,
step-time distribution, validation, and frozen acceptance behavior. The goal is
not one universal “best config.” It is an evidence-backed operating point under
a declared constraint.

## Learning outcomes

By the end, you can:

- distinguish microbatch size, accumulation, data-parallel world size,
  sequences per update, token slots, nonpadding tokens, and supervised tokens;
- preserve optimizer-step semantics while sweeping microbatch and accumulation;
- explain why equal token slots do not guarantee equal useful tokens;
- identify when sequence length or packing changes the optimization problem;
- separate warmup, measurement, evaluation, and checkpoint time;
- read a PyTorch profiler trace by CPU operator, CUDA kernel, shape, and memory;
- explain activation checkpointing as compute-for-memory recomputation;
- compare BF16, FP16, and FP32 as separate numerical treatments;
- diagnose input starvation, compute saturation, allocator pressure, and
  synchronization stalls;
- record medians and tails rather than one lucky step;
- detect confounded result files automatically;
- find a Pareto frontier across throughput, peak memory, and validation loss;
- choose from that frontier using a predeclared capacity/cost constraint;
- avoid turning synthetic fixtures or planning arithmetic into benchmark claims.

## What you will build

The required lab produces:

- `study-plan.json`, containing immutable study inputs, candidate arithmetic,
  warmup/measurement policy, and required metrics;
- `fixture-pareto.json`, proving the analyzer can retain throughput-heavy and
  memory-heavy choices while removing a dominated treatment;
- `expected-confound-failure.txt`, showing that changed data, run length, and
  token slots invalidate comparison.

The checked treatments keep sequence length at 512 and eight sequences per
optimizer update:

```text
baseline:          1 × 8 × 512 = 4096 slots
larger microbatch: 2 × 4 × 512 = 4096 slots
checkpointed:      1 × 8 × 512 = 4096 slots
FP32 control:      1 × 8 × 512 = 4096 slots
```

Only the named systems control changes. The real runs must still report actual
nonpadding and supervised tokens because 4096 is capacity, not work.

The optional path generates one effective lesson 35 configuration per
candidate, invokes the same training implementation, and binds every run to the
study and dataset-manifest hashes. The launcher sets the study's frozen seed,
checks its model/revision/optimizer/rate/decay/step/clipping invariants against
the executable base configuration, and rejects a packed-layout or DataLoader
worker treatment because lesson 35 does not implement those controls.
`profile_step.py` creates a TensorBoard trace from a real CUDA training loop so
you can learn profiler mechanics before profiling a full language model.

## Files in this lesson

```text
37-training-performance-controls/
├── README.md
├── configs/
│   ├── layout-lengths.json
│   └── study.json
├── fixtures/
│   ├── analyzer-results.json
│   └── confounded-results.json
├── schemas/
│   └── study-result.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   ├── run-dataloader-probe.sh
│   ├── run-deliberate-failure.sh
│   └── run-gpu-sweep.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── analyze_results.py
    ├── dataloader_probe.py
    ├── detect_confounds.py
    ├── layout_accounting.py
    ├── plan_study.py
    ├── profile_step.py
    └── run_transformers_sweep.py
```

Generated traces, checkpoints, and measurements belong beneath ignored
`artifacts/`.

## Under the hood

### The units that prevent bad comparisons

One optimizer update can contain several microbatches, and distributed data
parallelism adds ranks:

```text
sequences/update = microbatch × accumulation × data-parallel ranks
```

If every sequence is padded to fixed length `L`, token slots equal that product
times `L`. Actual context tokens exclude padding. Supervised tokens also exclude
prompt labels masked with `-100`. When response lengths vary, two runs can have
the same slots and different loss denominators.

Record all three. If the loss implementation averages per token, a batch with
more supervised tokens contributes differently from a per-example average.
Packing may raise useful-token density while altering example boundaries,
position IDs, and attention. Preserve or explicitly version those semantics.

### Precision is storage plus arithmetic

BF16 and FP16 each use two bytes for stored values, but have different exponent
and mantissa ranges. FP16 training commonly uses dynamic loss scaling to avoid
underflow. BF16 often avoids that specific need but still has limited
precision. Tensor cores, accumulator dtype, optimizer state, layer-norm
handling, and framework autocast rules determine actual behavior.

Do not label a treatment merely “mixed precision.” Record autocast dtype,
parameter dtype, master/optimizer state, scaler settings, TF32 policy, relevant
kernel flags, and hardware support. Quality gates still apply.

### Sequence length and padding

Self-attention work and intermediate memory generally grow strongly with
sequence length, while modern kernels and grouped-query attention change exact
constants. Halving maximum length can dramatically change cost, but it also
changes which examples fit and how much context is available. That is not a
pure performance treatment unless the workload contract already bounds all
examples below both lengths.

Padding waste is:

```text
1 - nonpadding tokens / token slots
```

Packing fills slots with multiple examples. End tokens alone do not guarantee
isolation. Check whether the trainer resets positions and applies block
diagonal attention. If not, later examples can attend to earlier examples and
the objective changed.

### Gradient checkpointing

Ordinary autograd saves selected forward activations for backward. Activation
checkpointing discards some of them, then reruns forward regions during
backward. Peak activation memory falls; compute and often step time rise. It
does not shard parameters or optimizer state, and its benefit depends on which
regions dominate memory.

Use the profiler and CUDA peaks to locate the trade. If a smaller microbatch
already fits comfortably, checkpointing may only slow the run. If checkpointing
enables a larger microbatch, compare the full operating points rather than the
flag in isolation.

### Input pipeline and optimizer

GPU gaps may come from JSON parsing, tokenization, remote storage, decompression,
host-to-device copies, too few workers, too many workers, or synchronous
logging. Data-loader workers consume memory and have independent random states.
Pinned memory and nonblocking copies can help when the pipeline supports them;
they are not universal wins.

Optimizer choice changes memory and computation. AdamW often keeps FP32 first
and second moments. Fused or low-bit implementations can change state,
launches, numerics, and checkpoint format. If optimizer changes, name it as a
separate treatment and keep quality evidence.

### Profiling without profiling startup

First steps include model loading, allocator growth, lazy kernel setup,
compilation, cache warming, and page faults. A useful study separates:

1. initialization;
2. warmup optimizer updates;
3. measured steady-state updates;
4. validation;
5. checkpoint writes.

The checked policy excludes ten warmup updates and requires at least thirty
measured updates. For short educational runs, that is still noisy. Repeat
treatments and report distribution, not the fastest step.

`torch.profiler` itself adds overhead. Use it for attribution, then run a
lower-overhead timing treatment for final throughput. Synchronize CUDA around
manual timing because kernel launches are asynchronous.

### Pareto reasoning

A treatment dominates another when it is no worse on every declared objective
and strictly better on at least one. The supplied analyzer maximizes median
tokens/second while minimizing peak allocated GiB and validation loss.

Several treatments can remain on the frontier. Choose using a rule declared
before inspection, for example:

- must fit below 20 GiB allocated with 20% headroom;
- must preserve every lesson 34 safety-slice gate;
- among eligible runs, minimize cost per million supervised tokens.

A weighted score can be useful, but weights selected after seeing winners are
another form of result shopping.

## Prerequisites and preflight

Complete lessons 35 and 36, including the CPU path and frozen data/evaluation
contracts:

```bash
cd lessons/phase-05-finetuning/37-training-performance-controls
python3 --version
python3 -m json.tool configs/study.json >/dev/null
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

For the GPU path, use the lesson 35 environment and confirm:

```bash
python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu", torch.cuda.get_device_name())
    print("allocated", torch.cuda.memory_allocated())
    print("reserved", torch.cuda.memory_reserved())
PY
```

Run lesson 33 to create the dataset manifest. The CPU runner and study planner
hash that exact generated manifest into `study-plan.json`; the source study
config deliberately contains no invented dataset hash.

Record driver, GPU clocks/power policy if visible, node type, CPU/memory,
storage/cache state, image digest, package versions, model revision, and
background workload. Use the same environment for every candidate.

## Cost and safety

The CPU lab is offline. Its fixture numbers are deliberately artificial and
must never appear in a hardware report.

The real sweep runs four training treatments. Estimate:

```text
total GPU time =
  candidates × (startup + warmup + measured steps + validation + checkpoint)
```

Set a wall-clock alarm and optimizer-step bound. Model downloads and image pulls
can occupy a GPU while doing no training; warm the cache before the measured
matrix if that is part of your study contract.

Do not benchmark a shared production cluster. Training can consume all GPU
memory, host memory, storage bandwidth, and network bandwidth. Use a lesson
namespace or isolated host, immutable inputs, and private data controls.

Stop the sweep on nonfinite loss, repeated OOM, changed provenance, or failed
safety evaluation. More trials do not repair an invalid experiment.

## Predict before running

Create `artifacts/predictions.md`:

1. Which checked candidate should use the most activation memory?
2. Which candidate is expected to trade compute for lower activation memory?
3. Do equal 4096 token slots prove equal supervised-token counts?
4. Can adding workers make a fully GPU-bound loop faster?
5. Why might the first optimizer steps be slower?
6. Does profiler time equal uninstrumented production time?
7. Is reserved CUDA memory the same as live tensor memory?
8. If validation improves after halving maximum sequence length, is the
   comparison necessarily fair?
9. Can a faster candidate be rejected for quality?
10. What rule will you use to choose among Pareto-efficient candidates?

## Lab outline

1. Freeze the study invariants and candidate matrix.
2. Calculate sequences and token slots per optimizer update.
3. Exercise invariant validation and Pareto analysis on labeled fixtures.
4. Reject a confounded “winner.”
5. Capture one CUDA profiler trace.
6. Run controlled Transformers candidates.
7. Separate warmup from measurement and validation.
8. Aggregate useful tokens, memory, time, quality, and cost.
9. Select from the Pareto frontier using a predeclared rule.
10. Retest the chosen configuration and document uncertainty.

## Step-by-step lab

### 1. Validate the study design

```bash
./scripts/run-cpu-lab.sh
python3 -m json.tool artifacts/study-plan.json
```

Expected shape:

```text
PASS: 4 candidates preserve 4096 token slots per optimizer step
PASS: 4 runs preserve frozen invariants
PASS: frontier=baseline,checkpointed,larger-microbatch; dominated=dominated-example
```

The frontier names come from a software fixture. They say nothing about Qwen or
your GPU.

Inspect each candidate's `sequences_per_optimizer_step`,
`token_slots_per_optimizer_step`, and `strictly_comparable_slot_budget`.
Explain why the FP32 treatment preserves nominal data/update semantics while
changing storage, kernels, and arithmetic. Inspect
`layout-accounting.json`; higher slot utilization is not permission to skip
position and attention-isolation checks.

### 2. Read the analyzer rather than one score

```bash
python3 -m json.tool artifacts/fixture-pareto.json
```

The fixture intentionally contains:

- a throughput-heavy point;
- a memory-heavy checkpointed point;
- a balanced baseline;
- one point worse on all objectives.

Change one fixture value and predict whether frontier membership changes.
Retain the `evidence_kind` label.

### 3. Capture a real profiler trace

On the CUDA host:

```bash
python src/profile_step.py \
  --output artifacts/profile \
  --steps 8 \
  --dimension 2048
python3 -m json.tool artifacts/profile/summary.json
tensorboard --logdir artifacts/profile/trace
```

Inspect CPU launch gaps, GEMM/GELU kernels, optimizer work, shapes, and memory.
The toy MLP teaches the UI; profile the language-model loop separately after
you can interpret it.

### 4. Isolate DataLoader behavior

After installing PyTorch, run:

```bash
./scripts/run-dataloader-probe.sh
```

This compares zero and two workers over deterministic synthetic rows. Their
checksums should match. Timings are local input-delivery evidence, not language
model throughput. Repeat both treatments, then instrument the real tokenizer
and storage path before selecting workers.

### 5. Run the controlled model sweep

```bash
../33-dataset-engineering-chat-templates/scripts/run-cpu-lab.sh
export ALLOW_LESSON_37_GPU_SWEEP=yes
./scripts/run-gpu-sweep.sh \
  ../33-dataset-engineering-chat-templates/artifacts/dataset
```

The runner creates an effective config inside each run directory and calls
lesson 35's transparent loop. It does not fabricate an aggregate winner. After
the run, extract only steady-state updates into a result file conforming to
`study-result.schema.json`.

For each candidate calculate:

```text
nonpadding tokens/s = measured nonpadding tokens / measured step seconds
supervised tokens/s = measured supervised tokens / measured step seconds
cost per million supervised tokens =
  hourly GPU price × measured hours / supervised tokens × 1,000,000
```

Use your actual current price and cite its retrieval time; the repository does
not freeze cloud prices.

### 6. Preserve quality

Run validation at the same optimizer steps. Serve the chosen checkpoints with
the same engine and decoding configuration, then apply lesson 34's frozen
acceptance set. A treatment that raises throughput but fails cost-safety or
exposure-safety is ineligible.

### 7. Build the real frontier

Produce a result JSON with real measurements and run:

```bash
python src/detect_confounds.py --input artifacts/gpu-results.json
python src/analyze_results.py \
  --input artifacts/gpu-results.json \
  --output artifacts/gpu-pareto.json
```

The analyzer requires thirty measured optimizer steps. Repeat the selected
treatment to detect one-off noise.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-confound-failure.txt
```

The attractive fixture secretly uses:

- a different dataset-manifest hash;
- only twenty maximum optimizer steps instead of fifty;
- 2048 token slots per update instead of 4096;
- only ten measured steps.

The validator identifies the first three invariants before the analyzer can
declare a winner. Shorter sequences and a different dataset may genuinely be
useful, but they answer a different question. Recovery is to restore the
frozen inputs or create a separately named study and baseline both treatments
within it.

As a live failure drill, change only maximum sequence length for one candidate
and prove the guard rejects it. Do not delete the failed record; retain it as
evidence of the caught confound.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 src/detect_confounds.py --input fixtures/analyzer-results.json
python3 -m json.tool artifacts/study-plan.json >/dev/null
python3 -m json.tool artifacts/fixture-pareto.json >/dev/null
```

For the GPU study, require:

```bash
python3 src/detect_confounds.py --input artifacts/gpu-results.json
python3 src/analyze_results.py \
  --input artifacts/gpu-results.json \
  --output artifacts/gpu-pareto.json
```

Manually verify model, data, seed, optimizer, learning rate, run length,
sequence semantics, evaluation, hardware, image, cache/warmup, and profiler
overhead. Check that every result has at least thirty measured updates and no
nonfinite values. Re-run the selected point once.

## Troubleshooting

If a candidate changes token slots, decide whether to adjust accumulation or
move it into a separate study. Do not suppress the check.

If useful-token throughput is absent, instrument nonpadding attention-mask sums
and non-`-100` label counts. Slot throughput alone rewards padding.

If profiler traces are empty, confirm the scheduled wait/warmup/active windows,
enough steps, trace directory permissions, and CUDA activity support.

If manual CUDA timings look too small, add synchronization around the measured
region. GPU launches are asynchronous.

If allocated memory falls but reserved memory stays high, inspect the caching
allocator and fragmentation. Neither metric alone is sufficient.

If a multi-worker DataLoader is slower, inspect CPU saturation, process startup,
serialization, storage latency, worker count, prefetch depth, and whether data
was already cached.

If packing improves tokens/s but quality changes, inspect example boundaries,
position IDs, attention isolation, loss normalization, and truncation.

If repeated runs vary, report distributions and environment differences. Do
not select the fastest repeat.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── study-plan.json
├── layout-accounting.json
├── fixture-pareto.json
├── expected-confound-failure.txt
├── profile/
│   ├── summary.json
│   └── trace/
├── dataloader/
│   ├── workers-0.json
│   └── workers-2.json
├── gpu-sweep/
│   └── <candidate>/
│       ├── effective-config.json
│       ├── study-provenance.json
│       ├── train-log.jsonl
│       └── summary.json
├── gpu-results.json
├── gpu-pareto.json
└── report.md
```

The report must separate fixture behavior from measurements and include
invariants, warmup, measured-step count, medians/tails, nonpadding and
supervised throughput, allocated/reserved VRAM, validation and acceptance,
checkpoint overhead, hourly-price retrieval time, cost calculation,
uncertainty, selection rule, and cleanup.

## Exercises

1. Add FP32 and BF16 treatments with identical optimizer semantics.
2. Add gradient checkpointing at different layer granularities.
3. Instrument data wait, H2D copy, forward, backward, optimizer, and checkpoint.
4. Compare allocated, reserved, and host memory.
5. Add a packing treatment with verified block-diagonal attention.
6. Sweep data-loader workers and prefetch depth without changing order.
7. Compare fused and unfused AdamW as named treatments.
8. Add repeated runs and bootstrap uncertainty for median step time.
9. Calculate cost per accepted checkpoint, not only per token.
10. Detect a changed package or image digest as a confound.
11. Visualize the three-objective Pareto frontier.
12. Write a stopping rule for OOM and nonfinite loss.

## Completion gate

You are done when:

- checked candidates preserve the declared optimizer-step workload;
- fixture outputs are never described as GPU measurements;
- the deliberate data/run-length/token confound fails closed;
- a real profiler trace attributes work and its own overhead is acknowledged;
- every measured treatment records useful tokens, time, allocated/reserved
  memory, validation, and acceptance;
- warmup and checkpoint time are separately reported;
- the real result file passes invariant validation;
- the chosen treatment lies on the measured Pareto frontier and satisfies a
  predeclared constraint;
- the selected point is repeated and its uncertainty reported;
- no performance gain bypasses the frozen quality/safety gates.

## Cleanup

Local:

```bash
rm -rf -- artifacts
deactivate 2>/dev/null || true
```

Remove profiler traces and rejected checkpoints only after retaining approved
aggregates and provenance; traces can be large and may reveal operation names
or shapes.

For cloud runs, terminate Jobs, verify PVC/object-store retention, and restore
the GPU node group to the capacity recorded before the study. Query Kubernetes
and cloud resources separately. A stopped Python process does not prove the
node or storage stopped billing.

## Primary references

Sources were reviewed on 2026-10-21:

- [PyTorch profiler](https://docs.pytorch.org/docs/stable/profiler.html)
- [PyTorch profiler recipe](https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html)
- [PyTorch activation checkpointing](https://docs.pytorch.org/docs/stable/checkpoint.html)
- [PyTorch automatic mixed precision](https://docs.pytorch.org/docs/stable/amp.html)
- [PyTorch DataLoader](https://docs.pytorch.org/docs/stable/data.html)
- [PyTorch CUDA memory management](https://docs.pytorch.org/docs/stable/notes/cuda.html#memory-management)
- [Transformers padding and truncation](https://huggingface.co/docs/transformers/main/en/pad_truncation)
- [Transformers performance and scalability](https://huggingface.co/docs/transformers/main/en/perf_train_gpu_one)

The study planner, confound detector, Pareto analyzer, and deliberate failure
are author-validated. CUDA profiling and the Qwen sweep are real optional paths
but have not been executed on a live GPU in this draft.
