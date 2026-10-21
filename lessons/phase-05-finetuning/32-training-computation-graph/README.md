# 32 — What training adds to the computation graph

**Status:** draft
**Time:** 4–6 hours
**Compute:** `local-cpu`; optional `g1` for the CUDA measurement
**GPU budget:** zero for the required path; about 10 minutes for the optional path
**Prerequisites:** 01, 02, 17; lesson 23 is the normal course entry point
**Last reviewed:** 2026-10-21

## Why this matters

A model that serves on one GPU may be impossible to fully fine-tune on that same
GPU. Inference mostly needs weights, temporary forward activations, workspaces,
and—during autoregressive generation—a KV cache. Full training adds a backward
graph, parameter gradients, optimizer state, and sometimes full-precision master
weights. It also retains selected forward values until backward has consumed
them.

This lesson makes those additions concrete before a framework hides them. You
will train a tiny bigram language model using only the Python standard library.
The model is intentionally small enough that every parameter, gradient, AdamW
moment, saved activation, and update can be counted. You will then use the same
accounting categories for a seven-billion-parameter planning example. The
optional GPU path measures a real PyTorch forward and backward pass with and
without activation checkpointing.

The tiny model is not meant to produce useful prose. It preserves the important
state transitions:

```text
tokens
  -> logits from trainable weights
  -> softmax probabilities
  -> cross-entropy loss
  -> gradients
  -> clipping
  -> Adam first and second moments
  -> updated weights
```

If you can identify when each object appears, why it must remain alive, and
when it can be freed, LoRA, mixed precision, gradient accumulation, FSDP, and
ZeRO become variations on understandable mechanics rather than magic flags.

## Learning outcomes

By the end, you can:

- distinguish a forward inference graph from a training graph;
- derive the gradient of softmax cross-entropy at the logits;
- explain what automatic differentiation records during a forward pass;
- separate parameters, gradients, optimizer moments, master weights,
  activations, KV cache, and temporary workspaces;
- explain why `optimizer.zero_grad()` is a lifecycle operation, not ceremony;
- explain why AdamW normally uses more state than SGD;
- distinguish mixed precision compute from the dtype of optimizer state;
- explain how activation checkpointing trades recomputation for fewer retained
  activations;
- interpret PyTorch allocated, reserved, and peak memory without treating any
  one number as total device memory;
- reject the false conclusion that a serving-fit estimate proves training fit.

## What you will build

The required CPU lab creates two machine-readable artifacts:

1. `training-trace.json`, containing a deterministic bigram training run, loss
   samples, gradient clipping values, generation output, and an inventory of
   trainable and optimizer elements;
2. `memory-accounting.json`, containing explicit component-by-component memory
   estimates for BF16 inference, mixed-precision AdamW full training, and the
   same training case with fewer retained activations.

The verifier checks behavioral claims rather than one copied number. Loss must
fall materially, a full gradient slot must exist for every parameter, Adam must
have two moment slots per parameter, and the three memory cases must have the
expected ordering.

The optional GPU lab creates two fresh-process PyTorch measurements:

- `cuda-no-checkpoint.json`;
- `cuda-checkpoint.json`.

You compare peaks, but you do not assume checkpointing wins for every shape or
that PyTorch's allocator metrics include memory owned by the driver, another
library, or another process.

## Files in this lesson

```text
32-training-computation-graph/
├── README.md
├── configs/
│   └── memory-cases.json
├── results.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   ├── run-cuda-probe.sh
│   └── verify.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── memory_accounting.py
    ├── torch_cuda_probe.py
    └── train_trace.py
```

Generated evidence goes under the ignored `artifacts/` directory unless you set
`ARTIFACT_DIR` to another safe local path. Inspect artifacts before sharing;
the optional GPU result records the device name and software version.

## Under the hood

### Forward and backward

For one bigram example, the input token selects one row of a weight matrix. That
row is the logits vector. Softmax converts logits `z` into probabilities:

```text
p_i = exp(z_i) / sum_j exp(z_j)
```

Cross-entropy for target `y` is `-log(p_y)`. Its derivative with respect to a
logit is:

```text
dL/dz_i = p_i - 1(i == y)
```

Open `src/train_trace.py` and find that exact operation. The program accumulates
the derivative into the selected weight row and averages it across examples.
A deep transformer applies the chain rule through many more operations, but the
principle is the same. Autograd records enough relationships and saved tensors
in the forward pass to evaluate those derivatives in reverse order.

An inference context such as `torch.no_grad()` prevents construction of that
backward graph. It does not make the model weightless and it does not remove the
KV cache required by autoregressive serving. Conversely, training a full
sequence usually does not preserve an inference KV cache across optimizer
steps; it retains forward values needed to differentiate the loss.

### Gradients and accumulation

Gradients normally have the same shape as the trainable parameter they update.
Calling backward multiple times without clearing them accumulates values into
the existing gradient buffers. Gradient accumulation uses this deliberately:
several microbatches contribute scaled gradients before one optimizer step.
Accidental accumulation silently changes the effective batch and update.

The lesson clips the global gradient norm. If the norm is larger than the
configured bound, all gradients receive the same scale. This preserves their
direction while bounding magnitude. Clipping can prevent unstable updates, but
constant clipping can also signal a bad learning rate, bad data, or a loss
scaling problem.

### AdamW state

Adam tracks an exponential moving average of gradients and of squared
gradients. These are commonly called the first and second moments. That is two
state elements per trained parameter, in addition to the parameter and its
gradient. Mixed-precision implementations often maintain these moments in FP32,
and may maintain an FP32 master copy while BF16 or FP16 weights participate in
the forward pass.

The planning fixture therefore assigns, per parameter:

```text
BF16 weight             2 bytes
BF16 gradient           2 bytes
FP32 Adam first moment  4 bytes
FP32 Adam second moment 4 bytes
FP32 master weight      4 bytes
```

That simplified example reaches 16 bytes per parameter before retained
activations and workspaces. Real frameworks vary: gradients may be FP32,
master weights may be absent, an 8-bit optimizer may compress states, flattened
buffers may add padding, and sharding can partition states. State the
assumptions instead of memorizing one multiplier.

### Activations and checkpointing

Backward needs values from forward. Retaining every layer's outputs can dominate
memory at long sequence lengths. Activation checkpointing stores selected
boundaries and recomputes the missing forward regions during backward. It saves
retained activation memory but spends additional compute and can complicate
random-number handling or stateful operations.

The JSON planning cases provide retained activation elements explicitly.
`memory_accounting.py` does not claim it can derive this number solely from
parameter count. Architecture, batch, sequence length, attention
implementation, fused kernels, checkpoint boundaries, and compiler choices all
matter.

### Allocated is not total

The optional PyTorch script records:

- memory allocated to live tensors by PyTorch;
- peak allocated memory;
- peak memory reserved by PyTorch's caching allocator.

Reserved memory may be greater than allocated because freed blocks remain in
the allocator for reuse. `nvidia-smi` can show a larger process footprint
because CUDA contexts and allocations outside PyTorch are not all represented
by `memory_allocated()`. A capacity decision needs headroom and an observed
worst-case workload, not only a spreadsheet.

## Prerequisites and preflight

Run commands from this lesson directory:

```bash
cd lessons/phase-05-finetuning/32-training-computation-graph
python3 --version
bash --version | head -n 1
test -f src/train_trace.py
test -f configs/memory-cases.json
```

The required path uses the Python standard library and does not download a
model. Check that the output location is local and safe:

```bash
printf 'artifact directory: %s\n' "${ARTIFACT_DIR:-$PWD/artifacts}"
```

For the optional path, first verify the host and driver:

```bash
nvidia-smi
python3 -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
```

Install PyTorch using the command produced by the official PyTorch installation
selector for your operating system, package manager, and supported CUDA
version. Do not copy a CUDA wheel command from a different driver environment,
and do not replace an existing serving-engine environment in place. Use a
separate virtual environment.

## Cost and safety

The CPU path costs no cloud GPU time. Complete it first.

The optional probe should run on an already-approved `g1` lab node or
interactive GPU environment. It does not need EKS. The default tensor shape is
bounded, but shapes multiply memory quickly. Do not increase hidden size,
layers, batch, and sequence length together. A CUDA out-of-memory error can
leave allocator state in the Python process; the supplied script runs the two
configurations as separate processes.

Before using an AWS GPU node, record the intended duration and hourly price in
your region. Stop the instance or restore the EKS node group to its original
capacity immediately after the measurement. Never run the probe on a shared
production GPU.

## Predict before running

Write answers in `artifacts/predictions.md` before executing:

1. The bigram matrix contains 16 weights. How many gradient values and Adam
   moment values will full training allocate?
2. Which fixture should use more planned memory: BF16 inference or
   mixed-precision AdamW full training? List the components responsible.
3. Does activation checkpointing reduce weight memory, gradient memory, or
   optimizer-state memory?
4. Why can checkpointing increase step time?
5. Should `peak_reserved` be expected to equal `peak_allocated`?
6. If final loss falls, does that alone prove a useful general-purpose model?

Do not change predictions after seeing results. Add an observed column later.

## Lab outline

1. Inspect the tiny model and derive its loss gradient.
2. Run a deterministic training update sequence.
3. Inspect parameter, gradient, and optimizer-state counts.
4. Calculate explicit memory cases.
5. Change one memory assumption and explain the delta.
6. Deliberately break the optimizer-state accounting.
7. Optionally measure real CUDA allocated and reserved peaks.
8. Write a short fit/no-fit decision with stated uncertainty.

## Step-by-step lab

### 1. Read the implementation before executing it

Locate the logits gradient and Adam state:

```bash
grep -n "probability" src/train_trace.py
grep -n "first_moment\\|second_moment" src/train_trace.py
```

Confirm that loss is averaged and that the optimizer update happens after
gradient clipping. Sketch the tensor lifecycle:

```text
weights --forward--> probabilities --loss--> scalar
   ^                       |
   |                       v
Adam moments <--update-- gradients
```

### 2. Run the complete CPU lab

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

The final line should start with `PASS:` and state the properties that were
checked. You will also see three planned GiB totals. They are arithmetic
outputs, not claims that a seven-billion-parameter model was run.

Inspect the loss samples:

```bash
python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("artifacts/training-trace.json").read_text())
print("initial", result["initial_loss"])
print("final", result["final_loss"])
print("inventory", result["graph_inventory"])
print("generated", " ".join(result["generated_after"]))
PY
```

Expected shape:

```text
initial <positive number>
final <smaller positive number>
inventory {'gradient_elements': 16, ... 'optimizer_state_elements': 32}
generated <bos> ...
```

The exact loss is deterministic for the checked-in seed, but the verifier uses
a relative improvement gate to avoid teaching copy-the-number validation.

### 3. Inspect memory by component

```bash
python3 - <<'PY'
import json
from pathlib import Path

document = json.loads(Path("artifacts/memory-accounting.json").read_text())
for case in document["cases"]:
    print(f"\n{case['name']}: {case['total_gib']:.2f} GiB")
    for item in case["components"]:
        if item["bytes"]:
            print(f"  {item['name']:22s} {item['gib']:8.2f} GiB")
PY
```

Identify which components are present only for training and which inference
component is absent from the training examples. Do not infer that training can
never use a KV cache; specialized objectives and implementations may differ.
The point is to describe this workload's state.

### 4. Change one assumption

Copy the fixture into the ignored artifact directory:

```bash
cp configs/memory-cases.json artifacts/my-memory-cases.json
```

Change only `gradient_bytes_per_parameter` in the full-training case from `2`
to `4`, then recalculate:

```bash
python3 src/memory_accounting.py \
  --cases artifacts/my-memory-cases.json \
  --output artifacts/my-memory-result.json
```

Predict the byte delta before running. It should equal parameter count times
the additional bytes per gradient element. If the observed delta differs,
inspect whether you changed one or both training cases.

### 5. Optional CUDA comparison

Use a clean virtual environment containing a compatible PyTorch build, then:

```bash
./scripts/run-cuda-probe.sh
```

Compare results:

```bash
python3 - <<'PY'
import json
from pathlib import Path

for name in ("cuda-no-checkpoint.json", "cuda-checkpoint.json"):
    result = json.loads((Path("artifacts") / name).read_text())
    peak = result["bytes"]["peak_allocated"] / 1024**3
    reserved = result["bytes"]["peak_reserved"] / 1024**3
    print(name, f"allocated={peak:.3f} GiB reserved={reserved:.3f} GiB")
PY
```

Run each shape at least three times only if you are studying variance. The
provided helper already isolates checkpointed and uncheckpointed cases in fresh
processes. Record PyTorch version, device, shape, and whether the observed
difference agrees with your prediction.

## Deliberate failure

Break the memory contract without touching the original fixture:

```bash
cp artifacts/memory-accounting.json artifacts/broken-memory.json
python3 - <<'PY'
import json
from pathlib import Path

path = Path("artifacts/broken-memory.json")
document = json.loads(path.read_text())
case = next(
    item for item in document["cases"]
    if item["name"] == "full-training-adamw-mixed-precision"
)
optimizer = next(
    item for item in case["components"]
    if item["name"] == "optimizer_state"
)
case["total_bytes"] -= optimizer["bytes"]
case["total_gib"] = case["total_bytes"] / 1024**3
path.write_text(json.dumps(document, indent=2) + "\n")
PY

python3 scripts/verify.py \
  --trace artifacts/training-trace.json \
  --memory artifacts/broken-memory.json
```

The verifier should fail because the altered ordering no longer represents the
declared full AdamW case. Diagnose this as evidence corruption, not as a model
failure. Restore by regenerating from the source fixture:

```bash
./scripts/run-cpu-lab.sh
```

For an optional GPU failure drill, increase only sequence length until the probe
approaches the device limit. Do not start with an extreme value. Record the
last successful shape and the failing shape. A process exit after CUDA OOM is a
valid recovery; repeatedly reusing a damaged interactive process is not.

## Verification

Run the behavioral verifier independently:

```bash
python3 scripts/verify.py \
  --trace artifacts/training-trace.json \
  --memory artifacts/memory-accounting.json
```

Then verify JSON syntax and that no generated evidence is tracked:

```bash
python3 -m json.tool artifacts/training-trace.json >/dev/null
python3 -m json.tool artifacts/memory-accounting.json >/dev/null
git status --short -- artifacts
```

The completion evidence is valid when:

- the verifier prints `PASS`;
- loss decreases by the required relative amount;
- element counts match the code;
- your component delta calculation is correct;
- predictions have observed explanations;
- optional GPU claims include raw JSON, device, version, and exact shape.

## Troubleshooting

`Permission denied` for a helper means the executable bit is missing. Run
`chmod +x scripts/*.sh`; contributors must commit that mode.

If loss does not fall, confirm that you did not change the seed, learning rate,
number of steps, softmax derivative, or update sign. An update that adds the
gradient performs ascent.

If JSON parsing fails, remove only generated `artifacts/` and rerun. Do not edit
the checked-in result schema to accommodate a malformed output.

If PyTorch imports but CUDA is false, inspect the installed build, driver, and
container GPU exposure. A CPU-only wheel cannot use a GPU. In Kubernetes,
failure to request `nvidia.com/gpu` can also leave the device unavailable even
when the node has one.

If checkpointing uses more peak memory for the tiny optional shape, preserve
the result. Small graphs, checkpoint bookkeeping, allocator reuse, and the
chosen checkpoint boundaries can outweigh savings. Increase only a justified
dimension, measure in fresh processes, and report the limitation rather than
deleting a contrary result.

## Evidence to collect

Keep locally:

```text
artifacts/
├── predictions.md
├── training-trace.json
├── memory-accounting.json
├── my-memory-cases.json
├── my-memory-result.json
├── cuda-no-checkpoint.json       # optional
├── cuda-checkpoint.json          # optional
└── report.md
```

`report.md` should answer:

- Which state exists during full training but not the supplied inference case?
- How many bytes per parameter did each case assume?
- Which number was measured and which number was modeled?
- What uncertainty or allocator overhead remains?
- Would the full-training case fit a 24 GiB device? Why is the answer obvious
  even before activations?
- Which later technique—LoRA, low-bit optimizer, checkpointing, FSDP, or
  ZeRO—targets each memory component?

## Exercises

1. Add an SGD-with-momentum case. Count its optimizer state and compare it with
   AdamW.
2. Change the tiny optimizer to plain SGD. Remove moment arrays and adjust the
   verifier.
3. Demonstrate accidental gradient accumulation by omitting a reset in a
   two-microbatch variant. Explain the changed update.
4. Add an effective-batch calculation:
   `microbatch × accumulation steps × data-parallel ranks`.
5. Derive the extra memory from changing gradients from BF16 to FP32 for 7B
   parameters, then confirm the calculator delta.
6. On GPU, sweep sequence length while keeping batch and model shape fixed.
   Plot peak allocated bytes against sequence length.
7. On GPU, use the PyTorch memory snapshot tooling to identify live tensor
   allocations. Clearly distinguish the snapshot from `nvidia-smi`.
8. Explain why sharding optimizer state helps fit training while ordinary DDP
   does not pool model memory across ranks.

## Completion gate

You are done when you can explain, without reading the solution:

1. the forward-to-backward dependency in the tiny language model;
2. why every fully trained parameter normally has a gradient slot;
3. why Adam adds two moment slots;
4. why mixed precision does not imply every state is low precision;
5. what checkpointing recomputes and what it does not shrink;
6. why allocator metrics need interpretation;
7. why a serving-fit model may still be far beyond one-GPU full-training
   capacity.

Your evidence must pass `scripts/verify.py`, and your report must label modeled
versus measured values.

## Cleanup

The required cleanup removes only ignored, regenerable lesson evidence:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

If you used a virtual environment inside this lesson, deactivate and remove it
only after confirming it contains no needed work. If you used an AWS GPU, stop
it or restore the lab node group to its saved starting capacity. Verify with
the same AWS or Kubernetes command used before scaling; deleting local JSON is
not cloud cleanup.

## Primary references

Sources were reviewed on 2026-10-21:

- [PyTorch autograd mechanics](https://docs.pytorch.org/docs/stable/notes/autograd.html)
- [PyTorch automatic mixed precision examples](https://docs.pytorch.org/docs/stable/notes/amp_examples.html)
- [PyTorch activation checkpointing](https://docs.pytorch.org/docs/stable/checkpoint.html)
- [PyTorch CUDA memory management](https://docs.pytorch.org/docs/stable/notes/cuda.html#cuda-memory-management)
- [Decoupled Weight Decay Regularization (AdamW)](https://arxiv.org/abs/1711.05101)
- [Training Deep Nets with Sublinear Memory Cost](https://arxiv.org/abs/1604.06174)

The CPU path is dependency-free and is the repository's author-validated path.
The optional PyTorch/CUDA path remains a learner measurement until it is run on
the target GPU environment and recorded in lesson validation metadata.
