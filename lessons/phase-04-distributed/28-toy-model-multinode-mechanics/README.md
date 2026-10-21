# 28 — Multi-node mechanics with a deterministic toy model

**Status:** draft
**Estimated time:** 6–8 hours
**Compute profile:** local CPU required; optional three separate one-GPU EKS
nodes
**Estimated GPU-minutes:** 45–90 optional
**Estimated cloud cost:** three GPU nodes for the bounded run plus normal EKS
and network charges; calculate from current Regional pricing
**Prerequisites:** lessons 24–27
**Last validated:** 2026-10-21
**Validated with:** Python 3.9 syntax and mathematical fixture tests; PyTorch
2.5.1 is pinned for the executable path; live Gloo/NCCL runs remain unvalidated

## Why this matters

Moving directly from a one-GPU server to a 30-billion-parameter distributed
checkpoint creates too many possible failures at once:

- model files can be missing or incompatible;
- weights may not fit;
- a tensor dimension may not divide by the shard count;
- rank discovery can fail;
- different ranks may load different revisions;
- collectives can be ordered incorrectly; and
- output can be plausible but numerically wrong.

A tiny deterministic model removes download, license, storage, and memory
pressure. You can print every tensor shape and calculate the expected output.
The same tensor-parallel mechanics—column sharding, row sharding, and an
all-reduce—appear inside larger engines.

Correctness comes first. A distributed system that returns different logits
from the reference is not “a little slower”; it is broken.

## Learning outcomes

By the end, you can:

- implement a column-parallel linear layer followed by a row-parallel layer;
- explain why the hidden dimension must divide by TP=3;
- derive each rank's weight slice and activation shape;
- use all-reduce to sum row-parallel partial outputs;
- compare distributed output to a single-process reference;
- verify all ranks use the same seed/configuration hash;
- distinguish rank discovery from model-shard correctness;
- run the same code with Gloo on CPU and NCCL on three GPU nodes;
- diagnose invalid divisibility, mismatched configuration, and missing rank
  failures; and
- retain an auditable tensor-shape and output record.

## What you will build

The toy network is:

```text
input X [batch=2, in=6]
        |
        +--> rank 0: W1 columns 0..3  -> H0 [2,4] -> W2 rows 0..3  -> P0 [2,6]
        +--> rank 1: W1 columns 4..7  -> H1 [2,4] -> W2 rows 4..7  -> P1 [2,6]
        +--> rank 2: W1 columns 8..11 -> H2 [2,4] -> W2 rows 8..11 -> P2 [2,6]
                                                                    |
                                           all-reduce P0 + P1 + P2
                                                                    |
                                                       add output bias
                                                                    |
                                                   output Y [2,6]
```

Rank 0 also evaluates the unsplit model and requires
`torch.testing.assert_close(distributed, reference)`. The summary JSON records
shard ranges, shapes, configuration hashes, maximum absolute error, and timing.

## Files in this lesson

```text
28-toy-model-multinode-mechanics/
├── README.md
├── requirements.txt
├── inputs/
│   └── request.json
├── src/
│   ├── toy_tp.py
│   └── arithmetic_fixture.py
├── k8s/
│   └── toy-tp.yaml.tpl
└── scripts/
    ├── test-arithmetic.sh
    ├── run-local.sh
    ├── render.py
    ├── deploy.sh
    └── observe.sh
```

Run commands from this directory. Kubernetes safety helpers are in
`../common/scripts/`.

## Concepts and mental model

A linear layer normally computes:

```text
Y = XW + b
```

For the first layer, split `W1` by output columns:

```text
W1 = [W1_0 | W1_1 | W1_2]
H_r = relu(X @ W1_r + b1_r)
```

Each rank independently computes a different hidden slice. No reduction is
needed yet because concatenating `H0`, `H1`, and `H2` reconstructs the complete
hidden activation.

For the second layer, split `W2` by input rows aligned with those hidden slices:

```text
W2 = vertical_stack(W2_0, W2_1, W2_2)
P_r = H_r @ W2_r
Y = all_reduce_sum(P_r) + b2
```

Every `P_r` has the full output width but contains only one shard's
contribution. All-reduce sums them and returns the full result to every rank.

The model is deterministic because the seed, dimensions, dtype, and input are
part of a canonical JSON configuration. Every rank hashes that configuration,
all-gathers hashes, and refuses to compute if they differ.

## Under the hood

With hidden size 12 and TP=3:

```text
hidden_per_rank = 12 / 3 = 4
```

Rank `r` owns `[r×4 : (r+1)×4]`. Shapes:

```text
X       [2, 6]
W1_r    [6, 4]
b1_r    [4]
H_r     [2, 4]
W2_r    [4, 6]
P_r     [2, 6]
Y       [2, 6]
```

This program creates the complete deterministic weights on each rank and then
slices them. That wastes memory but makes the teaching reference transparent.
Real engines avoid materializing complete weights on every rank by loading
rank-specific tensor slices from checkpoint files.

The all-reduce is semantically required, not merely a performance choice. If a
rank skips it, its output contains only a partial matrix product. If one rank
adds `b2` before the all-reduce, the bias is summed three times. The program
therefore adds output bias after reduction.

The reference and distributed paths run in the same dtype. Floating-point
association order can still create small differences, so correctness uses
explicit `rtol` and `atol` rather than exact string equality.

## Prerequisites and preflight

```bash
cd lessons/phase-04-distributed/28-toy-model-multinode-mechanics
chmod +x scripts/*.sh scripts/*.py src/*.py
python3 -m json.tool inputs/request.json
./scripts/test-arithmetic.sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For AWS:

```bash
export AWS_REGION='REPLACE_WITH_REGION'
export EKS_CLUSTER='REPLACE_WITH_CLUSTER'
export GPU_NODEGROUP='REPLACE_WITH_LAB_GPU_NODEGROUP'
export CONFIRM_GPU_NODEGROUP="$GPU_NODEGROUP"
export LAB_NAMESPACE='oms-distributed-28'
export PYTORCH_IMAGE='registry/repository@sha256:64_lowercase_hex_characters'
../common/scripts/assert-eks-target.sh
```

The image must contain the pinned-compatible PyTorch APIs and a CUDA/NCCL stack
compatible with the node driver. Record the image digest and runtime versions.

## Cost and safety

The complete correctness path works locally. Use GPUs only to validate the
transport/device version of the same mechanism. The model contains only
hundreds of values and cannot justify long-running nodes.

Cap the optional run at 90 GPU-minutes including node startup. The manifest
uses one GPU per Pod, required anti-affinity, exact node-group affinity, a
headless Service, and no storage or public endpoint. Stop immediately on a
configuration-hash mismatch or reference mismatch.

## Predict before running

1. What shape does each first-layer shard have?
2. Why does the second layer split rows rather than columns?
3. What happens if output bias is added before all-reduce?
4. Can hidden size 10 use TP=3?
5. Why can each rank build the same weights from one seed?
6. What evidence proves distributed output, not only process startup?

## Lab outline

1. Validate shard arithmetic without PyTorch.
2. run the unsplit and TP=3 paths locally.
3. inspect shapes, hashes, and maximum error.
4. break hidden-size divisibility.
5. break cross-rank configuration consistency.
6. optionally repeat one rank per GPU node.
7. collect logs and clean up.

## Step-by-step lab

### 1. Verify arithmetic fixture

```bash
./scripts/test-arithmetic.sh
python -m json.tool artifacts/arithmetic-fixture.json
```

This standard-library fixture uses integer matrix multiplication to show that
the sum of three row-sharded partial products equals the full result exactly.

### 2. Run TP=3 locally

After activating the venv:

```bash
./scripts/run-local.sh
python -m json.tool artifacts/local/summary.json
```

Expected contract:

```text
world_size: 3
hidden_size: 12
hidden_per_rank: 4
correctness.passed: true
max_absolute_error: near zero
```

All ranks should report the same configuration hash and different shard ranges.

### 3. Inspect rank ownership

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/local/summary.json").read_text())
for rank in d["ranks"]:
    print(rank["rank"], rank["hidden_range"], rank["shapes"])
PY
```

Check that ranges cover `[0,12)` exactly once and every partial output has shape
`[2,6]`.

### 4. Run on three GPU nodes

```bash
export I_UNDERSTAND_GPU_COSTS=yes
../common/scripts/scale-three-nodes.sh up
kubectl get nodes -o json |
  ../common/scripts/verify-three-gpu-nodes.py \
    --nodegroup "$GPU_NODEGROUP"
./scripts/render.py
./scripts/deploy.sh
./scripts/observe.sh
```

Then extract the rank-0 summary:

```bash
grep '^TOY_TP_SUMMARY=' artifacts/logs/rank-0.log |
  sed 's/^TOY_TP_SUMMARY=//' >artifacts/k8s-summary.json
python -m json.tool artifacts/k8s-summary.json
```

Require three unique host names and backend `nccl`.

## Inspect what happened

Read the code alongside the shapes:

```bash
sed -n '1,280p' src/toy_tp.py
kubectl -n "$LAB_NAMESPACE" get pods -o wide
grep -h '"event": "rank_shard"' artifacts/logs/*.log
```

Trace one output element:

```text
rank 0 partial[0,0]
+ rank 1 partial[0,0]
+ rank 2 partial[0,0]
+ bias2[0]
= distributed output[0,0]
```

The all-reduce combines partial values; it does not move the weight shards.

## Deliberate failure

### Invalid shape

```bash
set +e
torchrun --standalone --nproc-per-node=3 \
  src/toy_tp.py \
  --backend gloo \
  --hidden-size 10 \
  --output artifacts/invalid-shape.json
status=$?
set -e
printf 'exit=%s (nonzero expected)\n' "$status"
```

The program rejects the layout before allocating model tensors.

### Configuration mismatch

```bash
set +e
TOY_MISMATCH_RANK=2 torchrun --standalone --nproc-per-node=3 \
  src/toy_tp.py \
  --backend gloo \
  --output artifacts/mismatch.json
status=$?
set -e
```

Rank 2 changes its seed before hashing. Every rank gathers the hashes and raises
a clear mismatch instead of silently producing inconsistent shards.

## Controlled experiment

Change only batch size from two to eight:

```bash
torchrun --standalone --nproc-per-node=3 \
  src/toy_tp.py \
  --backend gloo \
  --batch-size 8 \
  --output artifacts/local/batch-8.json
```

Weight shapes and shard ownership stay constant; activation and partial-output
first dimensions become eight. Compare time only after correctness passes.

## Verification

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/local/summary.json").read_text())
assert d["correctness"]["passed"] is True
assert d["environment"]["world_size"] == 3
assert {tuple(r["hidden_range"]) for r in d["ranks"]} == {
    (0, 4), (4, 8), (8, 12)
}
assert len({r["config_hash"] for r in d["ranks"]}) == 1
assert d["measurements"]["max_absolute_error"] <= 1e-5
print("toy TP reference equivalence: PASS")
PY
```

## Expected result

The distributed and reference tensors match within tolerance. Each rank owns
four hidden features, all ranks finish one all-reduce, and the complete output
is available on every rank. Host names and timings vary. A nonzero but tiny
floating-point error can be valid; a large or shape-dependent difference is
not.

## Troubleshooting

| Layer | Symptom | Evidence |
|---|---|---|
| layout | hidden size rejection | hidden size modulo world size |
| launch | missing rank | rank environment logs and rendezvous endpoint |
| consistency | config hashes differ | canonical config printed by each rank |
| model | reference mismatch | shard ranges, bias placement, partial outputs |
| collective | timeout | last operation event from every rank |
| CUDA | Gloo works, NCCL fails | image/driver/device allocation/NCCL logs |
| scheduling | fewer than three hosts | Pod anti-affinity events and node count |

## Evidence to collect

- `artifacts/arithmetic-fixture.json`
- `artifacts/local/summary.json`
- invalid-shape and mismatch stderr
- optional `artifacts/k8s-summary.json`
- all rank logs and Pod placement
- `artifacts/report.md` tracing one output element

No model weights, token, or account identifier is involved. Sanitize
infrastructure evidence before sharing.

## Knowledge check

1. Why does column sharding produce different hidden features?
2. Why does row sharding produce addable partial outputs?
3. Where should the output bias be applied?
4. Which tensor crosses the network in this toy TP layer?
5. Why does a config hash protect correctness?
6. What limitation comes from constructing full weights on every rank?

## Exercises

Guided: add a second row-parallel output layer and count the resulting
collectives.

Independent: load each shard from its own JSON file rather than creating full
weights on every rank. Include a manifest hash and reject swapped shard files.

<details>
<summary>Solution outline</summary>

Each row-parallel output needs its own all-reduce. For sharded loading, create
files containing rank, global shape, slice range, values, and a hash of the
common model manifest. Verify all metadata before creating tensors.

</details>

## Completion gate

You pass when the arithmetic fixture and local TP run are correct, you can
derive every shape, both deliberate failures fail for the intended reason, and
you explain why correctness precedes performance. The optional GPU path must
also prove one rank per host and preserve a passing reference comparison.

## Cleanup

Local ranks exit automatically. For AWS:

```bash
../common/scripts/cleanup-namespace.sh
../common/scripts/scale-three-nodes.sh down
```

Verify the namespace is absent, scaling returned to the saved idle state, and
no selected nodes remain. This lesson creates no PVC or public Service.

## Primary references

Required, reviewed 2026-10-21:

- [Megatron-LM tensor parallelism paper](https://arxiv.org/abs/1909.08053)
- [PyTorch distributed overview](https://docs.pytorch.org/docs/stable/distributed.html)
- [PyTorch tensor parallel APIs](https://docs.pytorch.org/docs/stable/distributed.tensor.parallel.html)
- [NCCL collective operations](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html)

PyTorch `2.5.1` is pinned for the local teaching environment. The Kubernetes
image is separately digest-pinned and its actual bundled versions must be
recorded.
