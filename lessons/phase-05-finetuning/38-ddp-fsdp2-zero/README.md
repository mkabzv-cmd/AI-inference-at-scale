# 38 — Distributed training: DDP, FSDP2, and ZeRO

**Status:** draft
**Time:** 12–18 hours
**Compute:** `local-cpu` for collective mechanics; optional `g3` for three one-GPU nodes
**GPU budget:** zero for the required path; three-node experiments require explicit capacity and time approval
**Prerequisites:** 24–27, 37
**Last reviewed:** 2026-10-21

## Why this matters

“Distributed training” combines several different goals that are easy to
confuse:

- replicate a model to process more data in parallel;
- shard optimizer state to reduce per-rank memory;
- shard gradients;
- shard parameters so a model can fit;
- distribute checkpoints and recover them safely.

Distributed Data Parallel, or DDP, addresses the first goal. Every rank owns a
complete model replica, executes forward and backward on a different local
batch, and synchronizes gradients. Three one-GPU nodes do **not** automatically
turn into one larger memory pool. If the weights and ordinary training state do
not fit on one GPU, DDP alone does not make them fit.

PyTorch FSDP2 full sharding and DeepSpeed ZeRO-3 address state memory by
partitioning parameters, gradients, and optimizer state. That creates new
collectives, temporary materialization, checkpoint formats, and failure modes.
The network now sits on the training critical path. Ordinary G-series nodes can
teach all of these mechanisms even when they are much slower than tightly
connected training systems. The point of this course experiment is evidence,
not a claim that inexpensive Ethernet is an efficient way to train a huge
model.

The required path runs without PyTorch. It proves DDP gradient equivalence for
equal local batches, simulates reduce-scatter followed by all-gather, calculates
replicated versus sharded state, and deliberately demonstrates bias from
unequal local batch sizes. Optional files provide real `torchrun` DDP,
composable FSDP2, `torch.distributed.checkpoint`, DeepSpeed ZeRO-3, a rank-fail
drill, and a guarded three-node EKS Indexed Job.

## Learning outcomes

By the end, you can:

- define process, local rank, global rank, node rank, and world size;
- explain the DDP forward/backward/update sequence;
- prove when averaged rank gradients equal a single global-batch gradient;
- explain why unequal local batch sizes can bias an unweighted rank mean;
- state clearly that DDP does not pool model memory;
- distinguish parameter, gradient, optimizer, activation, and communication
  memory;
- explain ZeRO stages 1, 2, and 3;
- explain FSDP2 parameter all-gather and gradient reduce-scatter at a high
  level;
- calculate approximate ring all-reduce traffic;
- distinguish all-reduce, reduce-scatter, all-gather, broadcast, and barrier;
- explain bucketization and why compute/communication overlap matters;
- design one process per one-GPU G-series node;
- read NCCL and launcher failure evidence without assuming the network is the
  only cause;
- save and restore sharded checkpoints as a collective operation;
- explain why one failed rank usually terminates the worker group;
- choose DDP, ZeRO, or FSDP2 from memory, network, checkpoint, and operational
  constraints.

## What you will build

The required CPU lab creates:

- `collectives.json`, comparing three rank-local gradients with one
  concatenated-batch gradient and reconstructing an elementwise reduction from
  shards;
- `strategy-plan.json`, estimating state memory for DDP, ZeRO-1/2/3, and FSDP2
  full sharding over three ranks;
- `uneven-batches.json`, quantifying the error introduced by naïvely averaging
  rank means for local batch sizes one, two, and three;
- an expected nonzero deliberate-failure record.

The planner uses a hypothetical seven-billion-parameter model to make the
differences visible. It reports planning arithmetic, not observed VRAM and not
a guarantee that a configuration fits. It includes a largest-layer materialize
term and a fixed nonmodel reserve, but excludes activations, fragmentation,
temporary buffers, kernels, and checkpoint staging.

The optional PyTorch path can run a real three-process DDP equivalence check on
one CPU host with Gloo. The optional GPU path uses exactly three nodes with one
GPU process each. It includes:

- a DDP update checked against a single-process reference;
- an FSDP2 full-shard step and distributed checkpoint;
- a DeepSpeed ZeRO-3 step/checkpoint example;
- an intentional rank-1 exit;
- a private headless Service and Indexed Job with stable completion identities;
- strict immutable image, anti-affinity, GPU request, no public endpoint, and
  guarded cleanup.

## Files in this lesson

```text
38-ddp-fsdp2-zero/
├── README.md
├── requirements-distributed.txt
├── configs/
│   ├── deepspeed-zero3.json
│   └── strategy-study.json
├── k8s/
│   └── three-node-training.yaml.tpl
├── schemas/
│   └── strategy-plan.schema.json
├── scripts/
│   ├── cleanup-three-node.sh
│   ├── deploy-three-node.sh
│   ├── render-k8s.py
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   ├── run-local-ddp.sh
│   └── run-rank-failure.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── collective_simulator.py
    ├── ddp_equivalence.py
    ├── deepspeed_zero.py
    ├── fsdp2_checkpoint.py
    ├── rank_failure.py
    ├── strategy_planner.py
    └── uneven_batch_failure.py
```

Generated checkpoints, NCCL logs, traces, and rendered manifests belong under
ignored `artifacts/`.

## Under the hood

### DDP is replicated data parallelism

At the start, rank zero or the launcher ensures every rank has the same
parameters. Each rank receives a different local batch and computes local
gradients. DDP hooks group gradients into buckets and schedules reductions as
backward makes them ready. Conceptually:

```text
rank 0 local gradient g0
rank 1 local gradient g1
rank 2 local gradient g2
all-reduce SUM, then divide by 3
every rank receives (g0 + g1 + g2) / 3
every rank applies the same optimizer update
```

With equal local batch sizes and equivalent loss normalization, this equals the
gradient of the concatenated global batch. The CPU simulator and real
`ddp_equivalence.py` test that property.

Every rank still owns the full parameters, gradients, and ordinary optimizer
state. DDP can increase throughput when parallel compute outweighs
communication, but its per-rank model-state memory is approximately unchanged.
Activations depend on local microbatch and sequence length.

### Uneven input is a mathematical issue

Suppose ranks contribute one, two, and three examples. Averaging each rank's
mean gradient equally gives each rank one-third weight, not each sample
one-sixth weight. Possible solutions depend on the training contract:

- use a sampler that produces equal valid counts;
- weight local loss/gradients by actual sample or supervised-token counts;
- use appropriate distributed join semantics when ranks exhaust data;
- drop or explicitly pad batches and document the resulting data distribution.

Duplicating examples merely to equalize ranks changes sampling. Hanging when
one rank finishes early is a separate control-flow failure. Both require
evidence.

### Collective operations

An all-reduce combines tensors across ranks and returns the result to every
rank. Ring all-reduce is often described as a reduce-scatter phase followed by
all-gather. For tensor size `S` and world size `N`, a common approximate
per-rank traffic expression is:

```text
2 × (N - 1) / N × S
```

This counts bytes transferred under an idealized ring, not latency, protocol
overhead, retransmission, or topology effects.

Reduce-scatter combines corresponding input values while leaving each rank with
one shard. All-gather concatenates shards so every rank receives the full
result. FSDP/ZeRO-style systems use these patterns to avoid keeping all states
resident at all times. Broadcast sends one source tensor to others. Barrier
waits for all ranks and transfers no model tensor, although it still incurs
coordination.

NCCL chooses transports and algorithms based on topology and configuration.
On three separate ordinary G-series nodes, traffic crosses the instance network
rather than NVLink. You do not need EFA to learn correctness and failure
mechanics, but bandwidth/latency may make the run slow. Record actual interfaces
and NCCL logs; do not claim InfiniBand or RDMA merely because NCCL is present.

### ZeRO stages

Using the common conceptual breakdown:

- ZeRO-1 partitions optimizer state; parameters and gradients remain replicated.
- ZeRO-2 also partitions gradients.
- ZeRO-3 also partitions parameters and materializes what computation needs.

Exact buffer lifetimes, offload, prefetch, overlap, persistence thresholds, and
checkpoint layouts depend on implementation and configuration. CPU or NVMe
offload trades GPU memory for host memory, bandwidth, storage, and latency. It
is not free memory.

### FSDP2 full sharding

Composable FSDP2 applies `fully_shard` to modules. Parameters are represented in
distributed form between computation regions. Around a module's forward or
backward, ranks all-gather needed parameters; gradients can be
reduce-scattered, and optimizer state remains aligned with local shards.
Sharding smaller units lowers peak materialization but can increase collective
count and latency. Sharding only the whole model can require a much larger peak
all-gather.

Auto-wrapping decisions therefore affect both memory and network behavior.
Embeddings, tied weights, shared parameters, mixed precision, checkpointing,
and compilation need explicit handling.

### Memory arithmetic

The lesson uses these illustrative state bytes per parameter:

```text
BF16 parameter       2
BF16 gradient        2
FP32 master weight   4
FP32 Adam moments    8
full training state 16
```

For DDP, each rank carries the full 16-byte state in this model. ZeRO-1 divides
the 12 optimizer bytes by world size; ZeRO-2 also divides gradient bytes;
ZeRO-3/FSDP2 full shard divide all declared state. This is first-order
arithmetic. Actual peaks include module all-gathers, activations, CUDA/NCCL
buffers, allocator reservation, temporary reductions, and checkpoint
serialization.

A three-way shard is not guaranteed to fit a 24 GiB GPU merely because
`full_state/3 < 24 GiB`. Inspect the generated plan and its warning.

### Checkpoints are distributed state

A full state-dict gathered onto rank zero is portable but can exceed rank-zero
memory and create a network bottleneck. A sharded checkpoint lets each rank
write its local portion, often in parallel. It needs metadata describing tensor
layout and a coordinated commit. A directory where two ranks succeeded and one
failed is not a valid checkpoint.

The FSDP2 example uses `torch.distributed.checkpoint`. All ranks participate in
save. Restore should reconstruct model and optimizer state before resuming the
same scheduler/data position. Test resharding to a different world size rather
than assuming it works for every optimizer or format.

### Failure propagation

Collectives require matching participation. If rank one exits before a barrier
or all-reduce, other ranks wait until the process group detects failure or
times out. Elastic launchers may restart a group, but application state must
still roll back to a valid common checkpoint. Restarting only the failed rank
with newer or older optimizer state is inconsistent.

Set finite timeouts, enable useful NCCL diagnostics for the lab, retain logs
from every rank, and make Jobs fail visibly rather than retry indefinitely.

## Prerequisites and preflight

Run the required path:

```bash
cd lessons/phase-05-finetuning/38-ddp-fsdp2-zero
python3 --version
python3 -m json.tool configs/strategy-study.json >/dev/null
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

For local real DDP, create a Python 3.11+ environment and install the pinned
stack:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-distributed.txt
torchrun --help >/dev/null
```

For the EKS study, verify before scaling:

- current AWS identity, region, cluster, and context;
- starting desired/minimum/maximum node-group capacity;
- exactly three compatible one-GPU instances are allowed by quota and budget;
- each node advertises one healthy `nvidia.com/gpu`;
- the image is immutable and available to nodes;
- a ReadWriteMany claim is approved for distributed checkpoint output;
- DNS, rendezvous on TCP 29500, and trainer-to-trainer NCCL traffic work;
- three Pods can land on distinct hostnames;
- no production workload shares the experiment nodes unintentionally.

The supplied manifest does not create storage or scale nodes. Those external
actions stay explicit.

## Cost and safety

The CPU lab is free and offline. The optional study holds three GPU instances,
shared storage, and possibly model artifacts. Slow networking can lengthen
billable time even when GPU utilization is poor.

Set a maximum wall-clock duration and optimizer-step count. Start with the tiny
DDP equivalence or FSDP toy model, not a multi-billion-parameter training run.
Use one process per one-GPU node. Do not request privileged containers,
host networking, or host IPC merely to make NCCL errors disappear.

The EKS template uses a headless cluster-internal Service, indexed Job
identities, pod anti-affinity, no service-account token, non-root security, dropped
capabilities, one GPU request per Pod, an immutable image, and a namespace
NetworkPolicy. The policy allows traffic only among trainer Pods plus DNS;
peer traffic is not restricted to port 29500 because NCCL establishes data
connections in addition to the rendezvous store. It exposes no public
inference endpoint. The compatible image must run as UID/GID 10001; the Pod
uses the same `fsGroup` so all ranks can write the approved shared claim. The
policy document precedes the Service and Job in apply order.

Shared checkpoints may contain adapted model state and private-data
memorization. Encrypt and control them under the data policy. Namespace
deletion does not prove external shared storage or GPU capacity is cleaned up.

## Predict before running

Create `artifacts/predictions.md`:

1. Does DDP reduce weight bytes per rank?
2. When do averaged rank means equal a global sample mean?
3. Which ZeRO stage first partitions gradients?
4. Which strategies need parameter all-gathers during execution?
5. What idealized ring factor applies at world size three?
6. Why can `full state / 3` underpredict peak FSDP memory?
7. What happens to peers when rank one exits during a collective?
8. Can a partial sharded checkpoint be resumed safely?
9. Which evidence distinguishes DNS, network, and CUDA failures?
10. What benefit can three ordinary G nodes still provide if scaling is slow?

## Lab outline

1. Prove equal-batch DDP gradient equivalence.
2. Simulate reduce-scatter and all-gather.
3. Calculate per-rank replicated/sharded state.
4. Deliberately expose uneven-local-batch bias.
5. Run a real three-process CPU DDP equivalence test.
6. Trigger one rank failure and inspect launcher behavior.
7. Run toy FSDP2 and ZeRO-3 steps on three GPUs.
8. Save, inspect, corrupt, and restore a sharded checkpoint.
9. Deploy one process on each of three EKS G-series nodes.
10. Compare memory, communication, step time, recovery, and operations.

## Step-by-step lab

### 1. Run the dependency-free mechanics

```bash
./scripts/run-cpu-lab.sh
python3 -m json.tool artifacts/collectives.json
python3 -m json.tool artifacts/strategy-plan.json
```

Expected shape:

```text
PASS: equal-batch DDP mean equals the global mean; reduce-scatter plus all-gather reconstruction verified
PASS: wrote replication and sharding memory/traffic estimates
```

Check that every simulated rank has two examples and that
`maximum_update_difference` is below `1e-12`. Trace one element through the
three reduce inputs, reduction, shard, and reconstructed list.

### 2. Interpret the strategy plan

Print the planning totals:

```bash
python3 - <<'PY'
import json
from pathlib import Path

plan = json.loads(Path("artifacts/strategy-plan.json").read_text())
for name, value in plan["estimates"].items():
    print(name, round(value["planning_gib_with_nonmodel_reserve"], 2))
PY
```

Do not turn these values into fit claims. Instead, identify which state terms
are replicated or divided and list omitted peaks.

### 3. Run real DDP locally

After installing PyTorch:

```bash
./scripts/run-local-ddp.sh
python3 -m json.tool artifacts/torch-ddp-equivalence.json
```

`torchrun` starts three local Gloo processes. Each rank receives two distinct
samples, DDP reduces gradients, and rank zero compares the update with a
single-process batch of all six samples. Expected final line:

```text
PASS: DDP update equals a single global-batch update
```

This validates math and launcher wiring, not GPU performance.

### 4. Observe rank failure

```bash
./scripts/run-rank-failure.sh
sed -n '1,160p' artifacts/rank-failure.log
```

Rank one exits with code 42 before a barrier. The launcher should return
nonzero and terminate the group. Note how long peers take to discover failure
and which rank's root cause is easiest to find.

### 5. Run FSDP2/ZeRO on approved GPUs

For one host with three GPUs, a toy FSDP2 invocation is:

```bash
torchrun --standalone --nproc-per-node=3 \
  src/fsdp2_checkpoint.py \
  --checkpoint artifacts/fsdp2-checkpoint
```

For DeepSpeed:

```bash
deepspeed --num_gpus=3 src/deepspeed_zero.py \
  --config configs/deepspeed-zero3.json \
  --checkpoint artifacts/zero3-checkpoint \
  --steps 4
```

These toy models validate framework paths. Before substituting Qwen or a larger
model, port lesson 35's data/evaluation contract and add per-rank structured
logs, scheduler/data cursor, and immutable provenance.

### 6. Deploy three separate one-GPU nodes

Create or identify a compatible immutable training image containing this lesson
and the pinned dependencies. Record current capacity, then:

```bash
export IMAGE_REF="<registry>/distributed-trainer@sha256:<digest>"
export GPU_INSTANCE_TYPE="g5.xlarge"
export SHARED_CLAIM="<approved-read-write-many-claim>"
export ALLOW_LESSON_38_GPU_JOB=yes
./scripts/deploy-three-node.sh
```

Indexed completions zero, one, and two receive `JOB_COMPLETION_INDEX` as node
rank and stable indexed hostnames for peer discovery. Each runs one process and points to
`trainer-0.trainer-headless...:29500`. Pod anti-affinity requires distinct
Kubernetes nodes.

Inspect:

```bash
kubectl -n oms-l38 get pods -o wide
kubectl -n oms-l38 logs \
  -l batch.kubernetes.io/job-completion-index=0 -c trainer
kubectl -n oms-l38 logs \
  -l batch.kubernetes.io/job-completion-index=1 -c trainer
kubectl -n oms-l38 logs \
  -l batch.kubernetes.io/job-completion-index=2 -c trainer
```

Record NCCL interface/transport messages, per-rank allocated/reserved memory,
collective time, step time, and checkpoint files. Do not call the network
InfiniBand unless the underlying instance/network and logs prove it.

### 7. Recovery test

After a successful common checkpoint, stop the group, verify every declared
shard and metadata file, restart all ranks from that checkpoint, and compare
the next update against a continuous control run. Delete or rename one shard
in a copy and confirm restore fails rather than silently initializing missing
state.

## Deliberate failure

Required:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-uneven-failure.txt
python3 -m json.tool artifacts/uneven-batches.json
```

The script calculates local mean gradients for ranks with one, two, and three
samples. Their unweighted mean differs from the true six-sample mean and exits
nonzero intentionally. The wrapper requires that failure.

Recovery is not “ignore the difference.” Choose and document equal-count
sampling or correct sample/token weighting.

Optional distributed failures:

1. run `run-rank-failure.sh`;
2. delete one shard from a copied checkpoint;
3. block TCP 29500 and distinguish timeout from CUDA OOM;
4. deliberately schedule only two GPU nodes and inspect the Pending third Pod.

Always restore network policy and capacity. Do not perform failure injection on
shared production infrastructure.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 - <<'PY'
import json
from pathlib import Path

c = json.loads(Path("artifacts/collectives.json").read_text())
p = json.loads(Path("artifacts/strategy-plan.json").read_text())
u = json.loads(Path("artifacts/uneven-batches.json").read_text())
assert c["world_size"] == p["world_size"] == 3
assert c["maximum_update_difference"] < 1e-12
assert u["absolute_difference"] > 0
assert "does not pool model memory" in p["replication_rule"]
print("PASS: distributed invariants and failure evidence hold")
PY
```

For real distributed runs, require:

- identical initialization and immutable inputs on all ranks;
- exactly three unique global ranks and one GPU per process;
- equal or deliberately weighted local sample/token counts;
- per-rank memory and step/collective times;
- complete logs from every rank;
- valid common checkpoint metadata and shard set;
- a successful restore followed by an equivalent next update;
- nonzero group failure when one rank exits;
- no claim of DDP memory pooling;
- cleaned Kubernetes, storage, and node capacity.

## Troubleshooting

If processes hang at initialization, verify `MASTER_ADDR`, `MASTER_PORT`, DNS,
Pod readiness/address publication, NetworkPolicy, rank/world-size arguments,
and that rank zero is listening.

If NCCL selects an unexpected interface, inspect `NCCL_DEBUG=INFO`, container
interfaces, routes, security groups, and CNI behavior. Change interface
selection only after identifying the correct device.

If one rank OOMs, compare local batch/token lengths, data assignment, module
wrapping, device mapping, and rank-specific logging. One longer sequence can
create asymmetric activation memory.

If DDP is slower than one rank, calculate compute per rank versus gradient
bytes, bucket timing, network bandwidth/latency, and synchronization imbalance.
Correctness can still be the useful experiment outcome.

If FSDP peaks exceed the simple plan, inspect all-gather unit size, prefetch,
activation/checkpoint staging, allocator reservation, and unsharded modules.

If checkpoint save hangs, check that all ranks enter the same call, shared
storage is writable/mounted consistently, metadata creation succeeds, and no
rank failed earlier.

If an Indexed Job Pod remains Pending, inspect GPU allocatable resources,
anti-affinity, instance label, taints/tolerations, PVC mode, and events. Three
replicas require three distinct eligible nodes by design.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── collectives.json
├── strategy-plan.json
├── uneven-batches.json
├── expected-uneven-failure.txt
├── torch-ddp-equivalence.json
├── rank-failure.log
├── fsdp2-checkpoint/
├── zero3-checkpoint/
├── three-node-training.yaml
├── rank-0.log
├── rank-1.log
├── rank-2.log
├── environment.json
└── report.md
```

The report must state model/state arithmetic, actual per-rank peaks, wrapping
policy, collectives, bucket sizes, network evidence, local/global batch and
tokens, step distributions, checkpoint format/size/time, rank-failure
detection, recovery proof, cost window, and cleanup. Sanitize account, cluster,
registry, and private host identifiers before publication.

## Exercises

1. Generalize the simulator to world sizes two through eight.
2. Derive ring all-reduce bytes for a chosen gradient tensor.
3. Add sample-weighted reduction for uneven local batches.
4. Compare DDP `no_sync()` accumulation with synchronization every microbatch.
5. Change DDP bucket size and inspect overlap in a profiler trace.
6. Compare one-, two-, and three-rank scaling efficiency.
7. Apply FSDP2 at whole-model versus per-layer granularity.
8. Add mixed-precision policy and record sharded/compute/reduction dtypes.
9. Test resharding a checkpoint to a different world size.
10. Add a transactional completeness marker after all checkpoint shards commit.
11. Measure G-series Ethernet collective throughput with sanitized evidence.
12. Compare ZeRO-2 and ZeRO-3 memory/traffic for the same tiny model.

## Completion gate

You are done when:

- equal-batch DDP matches the single global-batch update;
- uneven rank input fails and its correction is explained;
- you can account for every replicated or sharded state term;
- you state why DDP does not fit a model whose weights exceed one GPU;
- all-reduce, reduce-scatter, and all-gather are traced with byte arithmetic;
- real local DDP succeeds if the optional dependency path is used;
- FSDP2/ZeRO evidence distinguishes planner estimates from measured peaks;
- one rank failure terminates or safely restarts the complete worker group;
- a sharded checkpoint is proven complete and restored;
- three-node Kubernetes placement, logs, network, storage, and cleanup are
  verified without unsupported NVLink/InfiniBand claims.

## Cleanup

Remove local generated files after retaining approved evidence:

```bash
rm -rf -- artifacts
deactivate 2>/dev/null || true
```

For EKS:

```bash
export ALLOW_LESSON_38_CLEANUP=yes
./scripts/cleanup-three-node.sh
```

Then query the external ReadWriteMany storage and apply its retention policy.
Restore desired/min/max GPU node-group capacity to the preflight values and
verify the nodes terminate. Check for snapshots, object-store shards, log
groups, and incomplete multipart uploads if your extension created them.
Namespace deletion alone is not financial cleanup.

## Primary references

Sources were reviewed on 2026-10-21:

- [PyTorch DistributedDataParallel](https://docs.pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html)
- [PyTorch distributed overview](https://docs.pytorch.org/tutorials/beginner/dist_overview.html)
- [PyTorch FSDP2 tutorial](https://docs.pytorch.org/tutorials/intermediate/FSDP_tutorial.html)
- [PyTorch composable fully_shard API](https://docs.pytorch.org/docs/stable/distributed.fsdp.fully_shard.html)
- [PyTorch distributed checkpoint](https://docs.pytorch.org/docs/stable/distributed.checkpoint.html)
- [DeepSpeed ZeRO documentation](https://deepspeed.readthedocs.io/en/latest/zero3.html)
- [ZeRO: Memory Optimizations Toward Training Trillion Parameter Models](https://arxiv.org/abs/1910.02054)
- [NVIDIA NCCL user guide](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
- [Kubernetes Indexed Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/#completion-mode)

The dependency-free collective, planner, and uneven-input failure paths are
author-validated. The PyTorch, FSDP2, DeepSpeed, NCCL, and EKS paths are
syntax/configuration drafts and have not been executed on live distributed
GPU infrastructure here.
