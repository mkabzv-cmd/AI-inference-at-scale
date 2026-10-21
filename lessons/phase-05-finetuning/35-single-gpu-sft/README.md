# 35 — Single-GPU supervised fine-tuning

**Status:** draft
**Time:** 8–12 hours
**Compute:** `local-cpu` for lifecycle mechanics; optional `g1` for the real model
**GPU budget:** zero for the required path; set a bounded one-GPU budget before the optional path
**Prerequisites:** 32–34
**Last reviewed:** 2026-10-21

## Why this matters

Supervised fine-tuning, or SFT, is the simplest useful adaptation loop for a
causal language model: show the model a prompt and desired answer, calculate
next-token loss, backpropagate, update parameters, and repeat. The definition is
short. A trustworthy run is not.

A training result depends on the exact model and tokenizer snapshots, chat
template, loss mask, dataset membership, example order, microbatch size,
accumulation, precision, optimizer, schedule, clipping, checkpoint state, and
evaluation contract. If any of those change during resume, the job may continue
without continuing the same experiment. If the loss mask is wrong, a perfectly
stable job optimizes the wrong tokens.

This lesson exposes that lifecycle before a trainer framework hides it. The
required CPU lab uses a tiny differentiable regression problem, not an LLM, so
you can inspect every optimizer step and prove that interruption plus resume is
identical to an uninterrupted run. It exercises the same control-plane
contract as model training:

```text
microbatches
  -> accumulated gradient
  -> gradient clipping
  -> optimizer update
  -> learning-rate schedule
  -> structured log
  -> checkpoint
  -> exact resume
```

The optional path is real SFT code built directly with PyTorch and
Transformers. It uses `Qwen/Qwen2.5-0.5B-Instruct` at immutable revision
`7ae557604adf67be50417f59c2c2f167def9a775`, consumes the versioned messages
from lesson 33, applies the pinned tokenizer's own chat template, creates
assistant-only labels, performs AdamW updates, records CUDA memory, validates,
checkpoints, and resumes. It deliberately avoids `Trainer` so you can trace the
mechanism.

The tiny course dataset cannot create a generally capable Kubernetes model.
The objective is to make the training system observable and falsifiable before
you spend money or trust a larger adaptation.

## Learning outcomes

By the end, you can:

- distinguish a microbatch, accumulated batch, optimizer step, epoch, and
  validation interval;
- explain why `loss / gradient_accumulation_steps` is needed before backward;
- trace causal language-model labels through the one-token shift performed by
  the model loss;
- construct assistant-only labels from the exact target chat template;
- explain why masked prompt tokens remain visible as context;
- use a one-example overfit test as a pipeline diagnostic, not a quality claim;
- interpret raw versus clipped gradient norms;
- index warmup and decay by optimizer updates rather than microbatches;
- identify the model, tokenizer, dataset, config, optimizer, scheduler, and RNG
  state required for an exact resume;
- estimate training state and checkpoint storage before allocating a GPU;
- package an offline model snapshot into an immutable container image;
- run a private, guarded Kubernetes Job and verify cleanup without claiming an
  unexecuted GPU result.

## What you will build

The required lab creates two optimizer histories:

1. twelve uninterrupted updates; and
2. five updates, a simulated interruption, then resume through update twelve.

`verify_lifecycle.py` requires every structured log record and final value to
match. It also verifies that early gradients were clipped, four microbatches
fed every optimizer update, and loss declined.

You will produce a planning-only memory report for a 0.494-billion-parameter
model. It separates weights, gradients, FP32 master weights, Adam moments, and
an explicitly approximate activation term. It is not presented as observed
VRAM.

For the optional GPU path, you will:

- build lesson 33's deterministic processed splits;
- run the pinned Qwen tokenizer over the original structured messages;
- verify that the prompt serialization is an exact prefix of the full
  conversation;
- train either a one-example overfit treatment or the bounded SFT treatment;
- interrupt only at an optimizer boundary;
- restore model, optimizer, scheduler, RNG, data cursor, config hash, and
  dataset-manifest hash;
- retain training JSONL, validation loss, checkpoints, and environment
  evidence;
- optionally deploy the same image as a private EKS Job with one GPU.

## Files in this lesson

```text
35-single-gpu-sft/
├── README.md
├── requirements-train.txt
├── configs/
│   ├── lifecycle.json
│   ├── overfit.json
│   └── sft.json
├── container/
│   └── Dockerfile
├── k8s/
│   └── training.yaml.tpl
├── schemas/
│   └── training-summary.schema.json
├── scripts/
│   ├── cleanup-gpu-job.sh
│   ├── deploy-gpu-job.sh
│   ├── render-k8s.py
│   ├── run-cpu-lab.sh
│   └── run-deliberate-failure.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── cache_model.py
    ├── lifecycle_simulator.py
    ├── resource_plan.py
    ├── train_transformers.py
    └── verify_lifecycle.py
```

Generated checkpoints and evidence belong under ignored `artifacts/`. Real
model weights and private data must not be committed.

## Under the hood

### The actual SFT target

For token IDs `x[0], ..., x[T-1]`, a causal model predicts a distribution for
the next position. Implementations conventionally align logits at positions
`0..T-2` with labels at `1..T-1`. The supplied script passes equal-length
`input_ids` and `labels`; `AutoModelForCausalLM` performs that shift internally.

Lesson 33's educational byte labels are useful for auditing boundaries, but
they are not Qwen token IDs. The real path therefore reads the stored
`messages` and calls the pinned tokenizer twice:

```python
prompt_ids = tokenizer.apply_chat_template(
    messages[:-1], tokenize=True, add_generation_prompt=True
)
full_ids = tokenizer.apply_chat_template(
    messages, tokenize=True, add_generation_prompt=False
)
```

It requires `prompt_ids == full_ids[:len(prompt_ids)]`. Labels for the prompt
prefix become `-100`; completion and template-terminator tokens retain their
IDs. `-100` tells PyTorch cross entropy to ignore those target positions. The
model still attends to system and user tokens.

If truncation removes every assistant target, the script stops. Silently
training an all-masked row would produce no useful learning signal. Silently
left-truncating the prompt could teach an answer without its required context.

### Accumulation and effective batch

Suppose microbatch loss gradients are `g1 ... gK`. To approximate the mean
gradient of their union, the loop backpropagates `loss/K` for each microbatch.
Gradients accumulate in parameter `.grad` buffers until one optimizer update:

```text
effective sequences/update =
  microbatch size × gradient accumulation steps × data-parallel ranks
```

That equation counts sequences, not useful tokens. Padding, truncation, packing,
and different response lengths change the number of context and supervised
tokens. The log therefore records supervised tokens as well as microbatches.

Accumulation does not reduce parameter, gradient, or ordinary optimizer-state
memory. It primarily trades step frequency and activation memory for more
forward/backward passes per update.

### Clipping and scheduling

Global norm clipping rescales gradients when their combined norm exceeds the
configured maximum. It is a guardrail, not a cure for an invalid objective.
Record the norm before clipping; recording only the capped value hides how
often the control activates.

Warmup and linear decay are indexed by optimizer step. With eight accumulated
microbatches, incrementing the scheduler after every microbatch would run it
eight times too quickly. The CPU reference makes this visible, while the real
loop calls `scheduler.step()` only after `optimizer.step()`.

### Exact checkpoint and resume

Model tensors alone are sufficient for inference but not for exact training
continuation. AdamW carries first and second moments. The schedule has a current
position. Random number generators influence dropout and sampling. The data
pipeline has a cursor or sampler state. Mixed-precision scaling may have state.

The optional script saves:

- model tensors and configuration;
- optimizer and scheduler states;
- CPU and CUDA RNG states;
- optimizer-step and microbatch cursor;
- training-config SHA-256;
- lesson 33 dataset-manifest SHA-256;
- immutable model and tokenizer revisions.

It saves only at optimizer boundaries. Checkpointing halfway through
accumulation would also require partial gradients and the exact set of consumed
microbatches.

The teaching loop uses deterministic cyclic order so cursor recovery is easy to
audit. A production shuffled sampler must checkpoint epoch, permutation,
position, worker seeds, and any streaming-shard state.

### Overfit before the full run

The one-example treatment asks a narrow question: can this exact data,
tokenizer, mask, model, optimizer, and checkpoint path drive training loss down
on one repeated example? Failure can reveal all-masked labels, an unfrozen
optimizer, wrong template, disconnected computation graph, extreme learning
rate, or broken input.

Success proves none of the following: held-out improvement, factuality, safety,
generalization, or absence of leakage. After the smoke test, delete or clearly
separate its checkpoint. Do not promote the memorized artifact.

### Memory and disk arithmetic

For full AdamW training in a common mixed-precision arrangement, a rough
parameter-state budget is:

```text
BF16 weights        2 bytes/parameter
BF16 gradients      2 bytes/parameter
FP32 master weights 4 bytes/parameter
FP32 Adam moments   8 bytes/parameter
```

That is roughly 16 bytes per parameter before activations, logits, CUDA
kernels, temporary buffers, allocator reservation, and fragmentation. Exact
implementations vary. Checkpoints may contain only serving weights or also
optimizer state; the latter is much larger. Run the planner, then measure both
`max_memory_allocated` and `max_memory_reserved` on the target stack.

## Prerequisites and preflight

Run the CPU path first:

```bash
cd lessons/phase-05-finetuning/35-single-gpu-sft
python3 --version
python3 -m json.tool configs/lifecycle.json >/dev/null
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Before a local GPU run, complete lessons 33 and 34:

```bash
../33-dataset-engineering-chat-templates/scripts/run-cpu-lab.sh
../34-evaluation-before-optimization/scripts/run-cpu-baseline.sh
test -f ../33-dataset-engineering-chat-templates/artifacts/dataset/manifest.json
```

Create an isolated Python 3.11 or newer environment on the CUDA host and install
the checked versions:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-train.txt
python - <<'PY'
import torch, transformers
print("torch", torch.__version__)
print("transformers", transformers.__version__)
print("cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu", torch.cuda.get_device_name(0))
    print("bf16", torch.cuda.is_bf16_supported())
PY
```

Confirm free disk and record `nvidia-smi`, driver version, container digest,
CUDA runtime, Python packages, and node start time. `configs/sft.json` requests
BF16 and must fail on hardware that does not support it; choose FP32 only as a
new recorded treatment.

For EKS, record current AWS identity, region, cluster context, node-group
capacity, PVC storage class, and intended duration before setting any guard
variable. The deployment script does not scale the node group for you.

## Cost and safety

The required CPU lab is offline and costs no cloud GPU time. The optional model
download consumes network and disk. The optional EKS Job requests one GPU and a
30 GiB dynamically provisioned volume; both may incur charges.

Set a time and optimizer-step limit before scaling. Use `backoffLimit: 0` so a
bad job does not repeatedly consume GPU time. The Job uses no Service, no public
endpoint, no service-account token, a non-root user, dropped capabilities, and
an immutable image reference. It also applies an ingress-and-egress deny
NetworkPolicy to the trainer. The model is cached during the image build, and
`HF_HUB_CACHE` points the offline runtime at that exact cache directory.
Pod UID/GID and `fsGroup` are all 10001 so the non-root trainer can write its
PVC-backed `/work` directory. The manifest creates the deny policy before the
Job, so the Pod is never intentionally started ahead of its boundary.
Confirm that the cluster's network-policy implementation enforces the policy;
offline environment variables alone are not a network boundary.

Do not bake credentials into the image. Public models normally need no token.
For a gated model, use an approved secret path at build/runtime and ensure logs,
layers, build history, and manifests do not retain it.

Never treat generated operational commands as authorized actions. The tiny
dataset includes safety language but does not enforce permissions.

## Predict before running

Create `artifacts/predictions.md` and answer:

1. With four microbatches per update and twelve updates, how many microbatches
   should the CPU log consume?
2. Should the learning-rate schedule advance during each backward call?
3. Which state would make a weights-only resume diverge under AdamW?
4. Will masked prompt tokens be invisible to attention?
5. What happens if maximum length ends before the first assistant token?
6. Why should the one-example overfit checkpoint never be called the winner?
7. Which memory terms remain when microbatch size falls from two to one?
8. Could two runs with identical loss curves still use different datasets?
9. What resource remains billable after a successful Job completes?
10. Which exact hashes should reject an incompatible resume?

Keep predictions unchanged and append observations.

## Lab outline

1. Inspect the lifecycle configuration and calculate update cadence.
2. Run the uninterrupted CPU optimizer history.
3. Interrupt after update five and resume from its checkpoint.
4. Prove complete record-by-record equivalence.
5. Inspect the memory and disk plan.
6. Deliberately change accumulation and reject the old checkpoint.
7. Build lesson 33 splits and run the optional one-example Qwen smoke test.
8. Run bounded full SFT, interrupt, resume, and evaluate.
9. Optionally package and execute a private EKS GPU Job.
10. Compare the tuned artifact with lesson 34's frozen contract.

## Step-by-step lab

### 1. Trace the required CPU run

```bash
./scripts/run-cpu-lab.sh
```

Expected shape:

```text
{"complete": true, ..., "optimizer_step": 12}
{"complete": false, ..., "optimizer_step": 5}
{"complete": true, ..., "optimizer_step": 12}
PASS: resume exactly matches uninterrupted run; loss ... -> ...
```

Inspect two updates:

```bash
sed -n '1p;$p' artifacts/full/train-log.jsonl
python3 -m json.tool artifacts/full/summary.json
```

Verify the arithmetic:

```bash
python3 - <<'PY'
import json
from pathlib import Path

rows = [
    json.loads(line)
    for line in Path("artifacts/full/train-log.jsonl").read_text().splitlines()
]
assert len(rows) == 12
assert rows[-1]["microbatches_consumed"] == 48
assert rows == [
    json.loads(line)
    for line in Path("artifacts/resumed/train-log.jsonl").read_text().splitlines()
]
print("PASS: 12 updates × 4 microbatches and exact resumed history")
PY
```

The regression weight need not reach its optimum. The bounded test checks
mechanics and direction, not convergence.

### 2. Inspect planning assumptions

```bash
python3 -m json.tool artifacts/resource-plan.json
```

Recalculate the parameter terms. Explain why the 25% headroom is a policy
choice rather than a guarantee. Compare the planner with actual CUDA peaks only
after a measured run.

### 3. Run the one-example model smoke test

On the approved CUDA host:

```bash
dataset_dir="../33-dataset-engineering-chat-templates/artifacts/dataset"
python src/train_transformers.py \
  --config configs/overfit.json \
  --dataset-dir "$dataset_dir" \
  --output artifacts/qwen-overfit
```

Inspect every logged step:

```bash
python3 - <<'PY'
import json
from pathlib import Path

rows = [
    json.loads(line)
    for line in Path("artifacts/qwen-overfit/train-log.jsonl").read_text().splitlines()
]
print("first", rows[0])
print("last", rows[-1])
PY
```

Do not demand a hard-coded loss. Confirm finite values, expected step count,
nonzero supervised tokens, and a meaningful downward tendency. If it does not
overfit, diagnose rather than extending the budget blindly.

### 4. Interrupt and resume bounded SFT

```bash
python src/train_transformers.py \
  --config configs/sft.json \
  --dataset-dir "$dataset_dir" \
  --output artifacts/qwen-sft \
  --stop-after 20

python src/train_transformers.py \
  --config configs/sft.json \
  --dataset-dir "$dataset_dir" \
  --output artifacts/qwen-sft \
  --resume artifacts/qwen-sft/checkpoint-000020
```

Expected evidence includes `train-log.jsonl`, checkpoints at declared
intervals, and `summary.json` with `"complete": true` and optimizer step 50.
The script rejects changed config or dataset hashes.

### 5. Evaluate, do not self-congratulate

Package or serve the final checkpoint privately, then run lesson 34's endpoint
evaluation unchanged. Preserve the base result even if the tuned result fails.
Training loss is not a release metric.

### 6. Optional EKS Job

Build from the repository root. Resolve the chosen CUDA-capable base image to an
immutable digest and pass it through `BASE_IMAGE`; do not use a mutable tag:

```bash
docker build \
  --build-arg BASE_IMAGE="<approved-cuda-image>@sha256:<digest>" \
  -f lessons/phase-05-finetuning/35-single-gpu-sft/container/Dockerfile \
  -t "<registry>/lesson35-sft:<build-id>" .
docker push "<registry>/lesson35-sft:<build-id>"
```

Resolve the pushed image digest, record it, then:

```bash
export IMAGE_REF="<registry>/lesson35-sft@sha256:<digest>"
export STORAGE_CLASS="<approved-ebs-csi-storage-class>"
export GPU_INSTANCE_TYPE="<existing-gpu-node-instance-type>"
export ALLOW_LESSON_35_GPU_JOB=yes
./scripts/deploy-gpu-job.sh
```

Watch events and logs in another terminal. Record the selected instance type as
part of the infrastructure treatment; the renderer does not assume a
particular G-series size.

## Deliberate failure

After the CPU lab:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-resume-failure.txt
```

The script changes accumulation from four to two and attempts to load the
step-five checkpoint. Tensor shapes still fit, but the config hash differs. It
must fail with `checkpoint configuration mismatch`.

Why fail? Accumulation changes data consumed per update and the meaning of
schedule position. Permitting the resume would splice two experiments into one
loss curve.

For a GPU extension, copy `configs/sft.json`, change one field, and prove the
real loop also rejects the previous checkpoint. Restore by using the original
config and dataset, or create a new experiment directory with explicit
warm-start provenance. Never overwrite the historical log.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 src/verify_lifecycle.py \
  --full artifacts/full \
  --resumed artifacts/resumed
python3 -m json.tool artifacts/resource-plan.json >/dev/null
```

For the real run, check:

```bash
python3 - <<'PY'
import json, math
from pathlib import Path

summary = json.loads(Path("artifacts/qwen-sft/summary.json").read_text())
rows = [
    json.loads(line)
    for line in Path("artifacts/qwen-sft/train-log.jsonl").read_text().splitlines()
]
assert summary["complete"]
assert summary["optimizer_step"] == 50
assert summary["model_revision"] == "7ae557604adf67be50417f59c2c2f167def9a775"
assert rows and all(math.isfinite(row["train_loss"]) for row in rows)
assert all(row["supervised_tokens"] > 0 for row in rows)
print("PASS: bounded SFT evidence is finite, complete, and pinned")
PY
```

Then verify the dataset manifest has not changed and run the frozen acceptance
evaluation. A completed training loop without evaluation is not completion.

## Troubleshooting

If loss is `nan`, inspect the first finite step, learning rate, precision,
inputs, gradient norm, and logits. Do not merely lower the rate until the error
disappears; first identify whether labels or data are invalid.

If every row reports no supervised tokens, inspect the exact template output
and truncation. Never infer role-token boundaries by searching decoded strings
after tokenization.

If the prompt is not a prefix of the full template, the tokenizer may add
different special tokens depending on the call. Save both ID lists and consult
the target model's documented template rather than weakening the assertion.

If resumed loss jumps, compare config and dataset hashes, optimizer/scheduler
state, RNG state, data cursor, precision, package versions, and hardware. The
script guarantees these core local fields but not bitwise equivalence across
different kernels or devices.

If the process is killed while writing a checkpoint, the directory may be
partial. Validate required files before resume and prefer atomic staging plus
rename in production.

If CUDA reports out of memory, capture allocated and reserved memory, sequence
lengths, and the failing operation. Reduce microbatch or sequence length as a
new treatment, consider checkpointing, then move to lesson 36. Do not assume
three DDP nodes pool memory; lesson 38 explains why.

If the Pod is Pending, inspect requests, allocatable GPUs, node labels, taints,
events, and PVC binding. If it completes but evidence vanishes, inspect the PVC
before deleting the namespace.

## Evidence to collect

Retain locally:

```text
artifacts/
├── predictions.md
├── full/
│   ├── train-log.jsonl
│   ├── summary.json
│   └── checkpoint-*.json
├── resumed/
├── resource-plan.json
├── expected-resume-failure.txt
├── qwen-overfit/                 # optional
├── qwen-sft/                     # optional
├── training.yaml                 # optional, sanitized
├── environment.json              # optional
└── report.md
```

`report.md` must include model/tokenizer revisions, package versions, image
digest, dataset manifest hash, configuration hash, hardware, precision,
microbatch and accumulation, token counts, optimizer-step schedule, clipping
frequency, CUDA allocated/reserved peaks, checkpoint/resume proof, validation
loss, frozen acceptance result, known nondeterminism, cost window, and cleanup
verification.

Do not publish private dataset samples, internal registry names, cluster
identifiers, or raw cloud account metadata.

## Exercises

1. Add momentum to the CPU optimizer and prove a weights-only resume diverges.
2. Checkpoint halfway through accumulation by saving partial gradients; explain
   the increased failure surface.
3. Implement stable shuffled ordering and checkpoint its permutation/cursor.
4. Compare prompt-only masking with full-conversation loss on one golden row.
5. Add a maximum prompt-length audit before tokenization truncates anything.
6. Measure CUDA allocated versus reserved peaks across sequence lengths.
7. Enable gradient checkpointing and explain compute-for-memory tradeoffs.
8. Compare BF16 and FP32 loss traces without calling tiny differences quality.
9. Add atomic checkpoint staging and a completeness marker.
10. Record exact raw responses from base and tuned endpoints under lesson 34.
11. Add an EBS snapshot-retention decision and quantify its continuing cost.
12. Explain how the loop must change for packed examples with block-diagonal
    attention.

## Completion gate

You are done when:

- the CPU uninterrupted and resumed logs match exactly;
- the incompatible resume fails closed;
- you can derive microbatches consumed from optimizer steps;
- you can identify the first supervised token in a real rendered row;
- the one-example smoke test either overfits or has a documented root cause;
- the bounded run records immutable model, tokenizer, dataset, and config
  provenance;
- interruption and resume retain optimizer, scheduler, RNG, and cursor state;
- all measured losses and memory values are preserved without invented claims;
- the tuned artifact is tested against lesson 34's unchanged acceptance set;
- any EKS resources, PVC policy, and GPU node capacity are independently
  verified after cleanup.

## Cleanup

For local generated evidence:

```bash
rm -rf -- artifacts
deactivate 2>/dev/null || true
```

For EKS, first copy approved evidence from the PVC. Then:

```bash
export ALLOW_LESSON_35_CLEANUP=yes
./scripts/cleanup-gpu-job.sh
```

Deleting the namespace deletes the lesson PVC under common dynamic-provisioning
policies, but volume and snapshot behavior depends on the storage class and
retention configuration. Query the Kubernetes PVC/PV and the owning cloud API.
Restore the GPU node group to the exact capacity recorded during preflight and
verify it. A completed Pod is not financial cleanup.

## Primary references

Sources were reviewed on 2026-10-21:

- [Pinned Qwen2.5-0.5B-Instruct snapshot](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)
- [Transformers chat templates](https://huggingface.co/docs/transformers/main/en/chat_templating)
- [Transformers causal language modeling](https://huggingface.co/docs/transformers/main/en/tasks/language_modeling)
- [PyTorch AdamW](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html)
- [PyTorch gradient clipping](https://docs.pytorch.org/docs/stable/generated/torch.nn.utils.clip_grad_norm_.html)
- [PyTorch saving and loading models](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)
- [PyTorch CUDA memory management](https://docs.pytorch.org/docs/stable/notes/cuda.html#memory-management)
- [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes security context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)

The dependency-free lifecycle, planning, resume, and failure paths are
author-validated. The PyTorch/Transformers implementation is syntax-validated
but has not been executed against a live GPU or EKS cluster in this draft.
