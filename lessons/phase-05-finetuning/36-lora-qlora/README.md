# 36 — LoRA and QLoRA from the matrix math

**Status:** draft
**Time:** 8–12 hours
**Compute:** `local-cpu` for matrix mechanics; optional `g1` for PEFT/QLoRA
**GPU budget:** zero for the required path; predeclare a bounded sweep budget for the optional path
**Prerequisites:** 35
**Last reviewed:** 2026-10-21

## Why this matters

Full fine-tuning updates every trainable model parameter and usually keeps
gradients plus optimizer state for all of them. Low-Rank Adaptation, or LoRA,
freezes the base model and learns a much smaller update for selected linear
layers. Quantized LoRA, commonly called QLoRA, also stores the frozen base in a
low-bit representation while computing adapter gradients in a higher
precision. These techniques make adaptation possible on hardware that cannot
hold an ordinary full-training state.

They are not magic compression switches. Rank controls the update subspace,
alpha controls scaling, target module names decide where capacity exists,
initialization decides the first gradient flow, dropout changes the training
path, quantization adds scales and numerical error, and merging changes the
serving artifact. An adapter is also incomplete without the exact base and
tokenizer revisions it was trained against.

This lesson starts with the matrix equation rather than a framework call:

```text
y = W x + s B A x

W: frozen out × in base matrix
A: trainable rank × in matrix
B: trainable out × rank matrix
s: alpha / rank in the classic LoRA scaling
```

The required lab implements forward, backward, initialization, parameter
counting, and merging with dependency-free Python. You will observe a subtle
but important fact: when `B` begins at zero, the initial adapter output is zero
and `A` receives zero gradient on the first backward pass, while `B` can move.
After `B` moves, gradients reach both factors.

The optional path uses the real PEFT and bitsandbytes stack with the same pinned
Qwen snapshot as lesson 35. It can run either BF16 LoRA or NF4 QLoRA, records
trainable parameters and CUDA memory, saves safetensors, and binds the adapter
to its data and base provenance. The course does not claim a quality or speed
winner without your measured result.

## Learning outcomes

By the end, you can:

- derive the shapes of `A`, `B`, and `B A` for one linear layer;
- calculate `rank × (in + out)` trainable parameters per targeted matrix;
- explain rank as a capacity constraint rather than a compression percentage;
- distinguish alpha, rank, and effective scaling;
- trace gradient flow under zero-`B` initialization;
- verify that frozen base weights receive no update;
- inspect actual module names before selecting PEFT targets;
- explain what NF4 represents and why QLoRA computation is not “training in
  four-bit arithmetic”;
- explain double quantization at a conceptual level;
- distinguish adapter storage, training memory, serving memory, and merged
  artifact size;
- merge a LoRA update algebraically and verify equivalent output;
- explain why an NF4-loaded base should not be treated as the canonical merge
  destination;
- package an adapter with exact base, tokenizer, data, config, and file hashes;
- select an adapter design from quality, VRAM, speed, and artifact evidence.

## What you will build

The CPU lab creates:

- `lora-math.json`, proving zero initial delta, first-pass gradient behavior,
  frozen base state, nonzero later gradients, and merged/unmerged equivalence;
- `sweep-plan.json`, calculating trainable parameters and storage for four
  rank/target treatments over the Qwen2.5 0.5B architecture;
- an expected failure showing that a plausible but nonexistent target module
  and an invalid direct NF4 merge policy are both rejected.

The checked sweep covers attention-only LoRA at ranks 4 and 8, plus all-linear
QLoRA at ranks 8 and 16. These are experiment candidates, not
recommendations. The planner reports exact arithmetic from declared
architecture dimensions but does not invent VRAM, throughput, or quality.

The optional GPU path consumes lesson 33's processed messages, renders the
pinned Qwen chat template, creates assistant-only labels, attaches PEFT
adapters, trains a bounded number of steps, saves the adapter and tokenizer, and
writes provenance. You then evaluate every candidate under lesson 34's frozen
contract and use lesson 37 for controlled performance comparison.

## Files in this lesson

```text
36-lora-qlora/
├── README.md
├── requirements-peft.txt
├── configs/
│   ├── available-modules.json
│   ├── invalid-sweep.json
│   └── sweep.json
├── schemas/
│   └── adapter-manifest.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   └── run-deliberate-failure.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── lora_math.py
    ├── package_adapter.py
    ├── peft_train.py
    └── plan_sweep.py
```

Generated adapters and measurements belong beneath ignored `artifacts/`.

## Under the hood

### Low-rank parameter arithmetic

For a base matrix `W` with shape `out × in`, a dense update would contain
`out × in` values. LoRA factors it into:

```text
A: rank × in
B: out × rank
trainable values = rank × in + out × rank
                 = rank × (in + out)
```

At rank 8, an 896-by-896 projection has `8 × (896 + 896) = 14,336`
adapter values instead of `802,816` dense values. Multiply by each occurrence
across layers and selected module types. Bias, embeddings, layer norms, and
saved metadata may add values depending on configuration.

The two-by-three CPU matrix deliberately uses rank two so both low-rank
directions are visible. Its ten adapter values exceed the six values in the
toy base matrix, so it is not a parameter-efficiency example. LoRA becomes
parameter-efficient only when `rank × (in + out) < in × out`, as it is for the
large projection above.

Parameter count does not equal peak memory. Training also needs adapter
gradients and optimizer state, while forward/backward needs activations,
quantization metadata, dequantization workspaces, CUDA kernels, and allocator
headroom. The planner reports BF16 adapter bytes and FP32 Adam moment bytes
separately so you do not confuse them with a measured peak.

### Rank, alpha, and initialization

Classic LoRA uses `s = alpha / rank`. Keeping `alpha = 2 × rank` gives scale
two across the checked candidates, but it does not make ranks equivalent.
Higher rank supplies more independent directions and more parameters. Other
implementations can use rank-stabilized scaling or different conventions;
record the library version and actual configuration.

A common initialization chooses nonzero random `A` and zero `B`. The initial
update `B A` is therefore zero, preserving base behavior before training. Let
`e = dL/dy`. Then:

```text
dL/dB = s e (A x)^T
dL/dA = s B^T e x^T
```

When `B = 0`, `dL/dA = 0` on the first pass but `dL/dB` can be nonzero.
This is expected, not evidence that `A` is permanently disconnected. Run
`lora_math.py` and inspect both gradient norms.

### Target modules are code, not paper labels

“Adapt attention” is not an executable target. PEFT matches module names such
as `q_proj` and `o_proj`. Names vary across architectures and implementations.
A configuration that resolves zero modules can produce an error, or a custom
wrapper might silently train something other than intended.

Before training:

```python
for name, module in model.named_modules():
    if isinstance(module, torch.nn.Linear):
        print(name, module.in_features, module.out_features)
```

Store the matched names and count. The checked
`available-modules.json` documents the expected suffixes for this specific
Qwen architecture, while the real run must inspect the loaded revision.

Attention-only targets reduce parameters and may be adequate for some tasks.
Adding gate/up/down MLP projections increases capacity and state. No target set
is universally best; use the frozen evaluation contract.

### QLoRA mechanics

In the optional QLoRA path, bitsandbytes loads the frozen base in 4-bit Normal
Float, or NF4, blocks. NF4 chooses representable levels suited to approximately
normal weight distributions. Scale metadata is needed to map codes back to
values. Double quantization compresses some of that quantization metadata.

During a linear operation, weights are dequantized or transformed into a
compute representation such as BF16 for the matrix multiplication. Activations,
adapter weights, adapter gradients, and optimizer states are not all four-bit.
The frozen quantized storage saves base-weight memory; backpropagation still
computes gradients through the operation into the adapters. The base has
`requires_grad=False`.

QLoRA may make a run fit, but it can change kernels, throughput, numerical
behavior, and serving choices. Measure it as its own treatment.

### Merge and artifact identity

After training:

```text
W_merged = W + s B A
```

The CPU reference verifies that `W_merged x` equals the unmerged adapter path
within floating-point tolerance. A merged artifact is convenient when a serving
engine cannot attach adapters or when you want one self-contained weight set.
An unmerged adapter is smaller, preserves base sharing, and can support multiple
named behaviors.

Do not blindly merge into the in-memory storage of an NF4 base and call it an
FP16 model. A conservative path is:

1. save and hash the adapter;
2. reload the exact base revision at the intended nonquantized serving dtype;
3. attach the adapter;
4. merge there;
5. save safetensors;
6. repeat frozen evaluation and serving benchmark;
7. preserve licenses and provenance for both inputs and output.

The adapter is not meaningful without the base revision and tokenizer. The
packaging script requires those hashes and rejects missing safetensors for a
real artifact.

## Prerequisites and preflight

Run lesson 35's CPU and model-data preparation first. Then:

```bash
cd lessons/phase-05-finetuning/36-lora-qlora
python3 --version
python3 -m json.tool configs/sweep.json >/dev/null
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

For the optional CUDA path, use an isolated Python 3.11 or newer environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-peft.txt
python - <<'PY'
import accelerate, bitsandbytes, peft, torch, transformers
print("torch", torch.__version__)
print("transformers", transformers.__version__)
print("peft", peft.__version__)
print("accelerate", accelerate.__version__)
print("bitsandbytes", bitsandbytes.__version__)
print("cuda", torch.cuda.is_available())
PY
```

Verify the lesson 33 manifest exists and record its SHA-256. Record driver,
GPU, free VRAM, package versions, model cache state, node start capacity, and
the lesson 34 evaluation lock before running.

Bitsandbytes support depends on platform, CUDA, and package build. The CPU lab
does not pretend to validate that integration.

## Cost and safety

The required path is offline and CPU-only. The optional sweep can multiply GPU
cost quickly: four candidates, overfit tests, full bounded runs, evaluation,
and serving checks are separate treatments. Set per-run steps and a total
wall-clock budget. Start with rank 4 or 8 attention-only, keep only successful
evidence, and stop GPU capacity between analysis sessions.

Adapters can memorize sensitive data even though they are small. Treat adapter
weights, optimizer checkpoints, logs, and generated samples under the same data
governance as full model weights. Do not commit them to this public repository.

Do not use private examples without approved collection, license, redaction,
retention, deletion, and access controls. Quantization is not anonymization.

If using EKS, reuse the private Job pattern from lesson 35. No public Service is
needed for training. Use immutable images, no embedded tokens, bounded retries,
and independently verify PVC and node cleanup.

## Predict before running

Write `artifacts/predictions.md`:

1. For an `out × in` layer, how many LoRA values are trained at rank `r`?
2. With zero `B`, which factor receives zero first-pass gradient?
3. Does higher rank imply better held-out quality?
4. Does `alpha/r` being equal make two ranks equivalent?
5. Will targeting MLP projections increase adapter size?
6. Are all QLoRA computations stored or executed in four-bit?
7. Why can a QLoRA adapter have FP32 optimizer moments?
8. Which artifact is smaller: merged weights or an unmerged adapter?
9. What exact base identity is needed to load an adapter?
10. Should a direct NF4-storage merge be accepted by the checked policy?

## Lab outline

1. Run the small matrix forward/backward path.
2. Inspect zero initialization and first/second gradient flow.
3. Merge the learned update and prove output equivalence.
4. Calculate candidate parameter and storage arithmetic.
5. Fail an invalid target and unsafe merge policy.
6. Inspect real model module names.
7. Run bounded LoRA and QLoRA treatments.
8. Package adapter safetensors with provenance.
9. Evaluate every candidate against the frozen contract.
10. Select one design from measured quality/resource evidence.

## Step-by-step lab

### 1. Execute the matrix reference

```bash
./scripts/run-cpu-lab.sh
python3 -m json.tool artifacts/lora-math.json
```

Expected shape:

```text
PASS: zero-B initialization, frozen W, adapter gradients, and merge equivalence verified
PASS: planned 4 valid adapter candidates
```

Inspect these fields:

- `initial_delta_is_zero` is true;
- `initial_gradient_a_squared_norm` is zero;
- `initial_gradient_b_squared_norm` is positive;
- `second_gradient_a_squared_norm` is positive;
- `base_weight_unchanged` is true;
- `maximum_merge_difference` is below `1e-12`.

Change alpha or rank in a copy of the script and predict how the scale changes
before rerunning.

### 2. Inspect the candidate plan

```bash
python3 -m json.tool artifacts/sweep-plan.json
```

Recalculate one attention-only and one all-linear candidate. Note that Qwen's
key/value projections use fewer output dimensions than query/output
projections because the declared architecture uses grouped-query attention.
Do not assume all four attention matrices are square.

The exact plan values are architecture arithmetic. Verify them against
`model.named_modules()` before treating them as runtime truth.

### 3. Inspect matched modules on the real model

On the CUDA host, load the exact snapshot and save all matching suffixes:

```bash
python - <<'PY' > artifacts/linear-modules.txt
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-0.5B-Instruct",
    revision="7ae557604adf67be50417f59c2c2f167def9a775",
    dtype="auto",
)
for name, module in model.named_modules():
    if module.__class__.__name__ == "Linear":
        print(name)
PY
```

Count matches for every configured target. Zero matches is a failed
configuration.

### 4. Run a bounded LoRA treatment

```bash
dataset_dir="../33-dataset-engineering-chat-templates/artifacts/dataset"
python src/peft_train.py \
  --dataset-dir "$dataset_dir" \
  --output artifacts/lora-r8 \
  --method lora \
  --rank 8 \
  --alpha 16 \
  --targets q_proj,k_proj,v_proj,o_proj \
  --steps 20
```

Expected files include `train-log.jsonl`, `provenance.json`, and
`adapter/adapter_model.safetensors`. Record the output of
`print_trainable_parameters()` and compare it with the planner. The effective
configuration and provenance also record every fully qualified module matched
by the requested suffixes; review that list instead of assuming a nonzero
total means the intended layers were selected.

### 5. Run QLoRA as a separate treatment

```bash
python src/peft_train.py \
  --dataset-dir "$dataset_dir" \
  --output artifacts/qlora-r8-all \
  --method qlora \
  --rank 8 \
  --alpha 16 \
  --targets q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj \
  --steps 20
```

Do not compare speed if either run includes model download, compilation, or
different warmup. Lesson 37 supplies a controlled method.

### 6. Package a real adapter

Hash the inputs and invoke:

```bash
dataset_sha="$(
  python3 -c 'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
  "$dataset_dir/manifest.json"
)"
config_sha="$(
  python3 -c 'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
  artifacts/lora-r8/effective-config.json
)"
python src/package_adapter.py \
  --adapter-dir artifacts/lora-r8/adapter \
  --base-model-id Qwen/Qwen2.5-0.5B-Instruct \
  --base-revision 7ae557604adf67be50417f59c2c2f167def9a775 \
  --dataset-manifest-sha256 "$dataset_sha" \
  --training-config-sha256 "$config_sha" \
  --output artifacts/lora-r8/adapter-manifest.json
```

Lesson 39 extends this into a release with cards, evaluation, benchmark, and
rollback evidence. The packager also checks the adapter configuration's
`base_model_name_or_path` and standard PEFT `revision` field against the
declared immutable base; caller-supplied provenance cannot relabel an adapter
trained over different bytes.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-plan-failure.txt
```

The fixture asks for `query_projection`, which is not an inspected target, and
requests `merge-directly-into-nf4-storage`. Both must appear in the failure.
This teaches two independent rules:

- a name that sounds correct is not a matched module;
- a quantized training representation is not automatically the desired merged
  serving representation.

Recover by selecting actual names from the pinned model and by saving the
adapter or reloading the nonquantized base before merge. Do not recover by
disabling validation.

As an extension, misspell only one module in a seven-module list and require the
entire run to fail. Partial targeting is not “close enough” when provenance
claims all seven.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 - <<'PY'
import json
from pathlib import Path

math = json.loads(Path("artifacts/lora-math.json").read_text())
plan = json.loads(Path("artifacts/sweep-plan.json").read_text())
assert math["base_weight_unchanged"]
assert math["maximum_merge_difference"] < 1e-12
assert len(plan["candidates"]) == 4
assert all(row["trainable_parameters"] > 0 for row in plan["candidates"])
print("PASS: matrix and sweep invariants hold")
PY
```

For every GPU candidate, require:

- exact model/tokenizer revision;
- exact matched target list and count;
- finite logs and declared step count;
- CUDA allocated/reserved peaks;
- adapter safetensors and PEFT config;
- data and training hashes;
- frozen validation and acceptance results;
- raw responses for failed items;
- no claim that unmeasured arithmetic is observed VRAM.

If you merge, compare logits or deterministic outputs between attached and
merged paths before and after serialization, then rerun evaluation.

## Troubleshooting

If PEFT reports no target modules, inspect actual names and wrapper nesting.
Suffix matching can select more modules than expected; store the full matched
list, not only suffixes.

If trainable parameter count is unexpectedly large, inspect embeddings, output
head, bias policy, `modules_to_save`, and target breadth.

If loss does not move on the first step, remember that zero-`B`
initialization can give `A` zero initial gradient. Confirm `B` has a gradient
and inspect later steps before diagnosing disconnection.

If bitsandbytes fails to import or initialize, verify supported OS, CUDA,
compute capability, wheel, driver, and PyTorch compatibility. Do not silently
fall back to a different precision while labeling the run QLoRA.

If CUDA memory exceeds the planner, inspect activations, sequence length,
temporary dequantization, optimizer state, gradient checkpointing, allocator
reservation, and which modules were actually targeted.

If merged and unmerged output differs materially, check scaling convention,
active adapter, dtype, dropout/eval mode, base revision, tokenizer, quantization
order, and whether the adapter was loaded twice.

If a saved adapter loads over the wrong base, stop. Similar architecture and
tensor shapes do not establish semantic compatibility.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── lora-math.json
├── sweep-plan.json
├── expected-plan-failure.txt
├── linear-modules.txt                 # optional GPU path
├── lora-r8/
│   ├── train-log.jsonl
│   ├── provenance.json
│   ├── adapter/
│   └── adapter-manifest.json
├── qlora-r8-all/                      # optional
├── comparison.json
└── report.md
```

The comparison must separate:

- trainable parameters;
- adapter bytes on disk;
- peak allocated and reserved VRAM;
- measured tokens/second after warmup;
- training/validation loss;
- every frozen acceptance slice and forbidden hit;
- attached versus merged serving behavior;
- base sharing and rollback consequences;
- run cost and cleanup status.

## Exercises

1. Implement rank-one LoRA and visualize its update matrix.
2. Use finite differences to check the analytic `A` and `B` gradients.
3. Compare zero-`B` and zero-`A` initialization.
4. Add rank-stabilized scaling as a separately named treatment.
5. Calculate Qwen parameter counts from inspected module shapes, not config.
6. Target only `q_proj` and compare capacity with all attention projections.
7. Measure the effect of `modules_to_save` on artifact size.
8. Inspect NF4 codes/scales for one synthetic weight block.
9. Compare QLoRA compute dtype BF16 and FP16 on supported hardware.
10. Verify base parameter gradients remain absent after backward.
11. Merge into a reloaded BF16 base and compare deterministic logits.
12. Serve two named adapters over one shared base and design isolation tests.

## Completion gate

You are done when:

- you can derive LoRA shapes and counts without PEFT;
- the CPU reference proves initialization, gradient, frozen-base, and merge
  behavior;
- invalid targets and merge order fail closed;
- real target names and matched counts come from the pinned model;
- LoRA and QLoRA candidates have separate immutable configs and evidence;
- adapter artifacts bind to base, tokenizer, data, and training hashes;
- measured resource values are not replaced by planner arithmetic;
- all candidates are evaluated against the same frozen contract;
- the selected rank/targets/method are justified by quality and resource
  constraints rather than folklore.

## Cleanup

Remove only generated local artifacts:

```bash
rm -rf -- artifacts
deactivate 2>/dev/null || true
```

If adapters were copied to object storage or a PVC, apply the approved
retention policy. Small artifacts still cost storage and can contain memorized
data. Remove rejected checkpoints only after preserving the comparison and
required audit evidence.

If you used an EKS GPU Job, delete its lesson resources, verify PVC/PV and any
snapshot state, restore the node group to its recorded starting capacity, and
query the owning cloud APIs. Do not infer cleanup from Pod deletion.

## Primary references

Sources were reviewed on 2026-10-21:

- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)
- [Hugging Face PEFT LoRA documentation](https://huggingface.co/docs/peft/main/en/package_reference/lora)
- [PEFT model merge documentation](https://huggingface.co/docs/peft/main/en/developer_guides/model_merging)
- [Transformers bitsandbytes quantization](https://huggingface.co/docs/transformers/main/en/quantization/bitsandbytes)
- [bitsandbytes official documentation](https://huggingface.co/docs/bitsandbytes/main/en/index)
- [Pinned Qwen2.5-0.5B-Instruct snapshot](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)

The dependency-free matrix, planner, and failure paths are author-validated.
The PEFT/QLoRA path is real source code and syntax-validated, but it has not
been executed on a live GPU in this draft.
