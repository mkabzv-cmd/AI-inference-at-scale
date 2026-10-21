# 27 — Characterize ordinary inter-node networking with NCCL

**Status:** draft
**Estimated time:** 6–9 hours
**Compute profile:** three separate one-GPU EKS nodes without assuming EFA,
RDMA, NVLink, or GPUDirect
**Estimated GPU-minutes:** 60–120
**Estimated cloud cost:** three GPU nodes for the bounded benchmark window,
standing EKS cost, and normal data processing/transfer terms that apply to your
network; calculate from current Regional pricing
**Prerequisites:** lessons 02, 24, and 26
**Last validated:** 2026-10-21
**Validated with:** Python 3.9 static syntax and fixture-based analyzer tests;
the CUDA/NCCL path has not been run on live G-series hardware

## Why this matters

If a model is slow across nodes, the engine is only one possible cause. Before
changing batching, quantization, or parallel layout, measure the communication
substrate with tensors whose meaning is simple.

This lesson deliberately targets the affordable, constrained case: one GPU per
node over the cluster's ordinary VPC network. It does not pretend that Ethernet
is NVLink or that a successful NCCL initialization proves EFA/RDMA use. Instead,
you will retain NCCL transport logs, node/Pod topology, message-size results,
and correctness checks.

Small messages reveal fixed latency and synchronization costs. Large messages
can approach a payload-rate regime. Tensor parallel decode often performs many
latency-sensitive collectives; pipeline parallelism sends larger activations at
stage boundaries. Measuring both regions helps predict which strategy will be
hurt more.

## Learning outcomes

By the end, you can:

- distinguish GPU-local, same-host, and inter-host paths;
- explain what NCCL provides beneath `torch.distributed`;
- inspect NCCL version, selected network interface, topology, and transport
  logs rather than assuming them;
- benchmark point-to-point round trip, all-reduce, and all-to-all operations;
- separate warm-up from measured iterations;
- calculate application payload rate and a clearly labelled all-reduce bus
  bandwidth convention;
- explain why payload rate is not line rate;
- compare two-rank participation with a three-rank collective;
- identify latency-sensitive and payload-sensitive regions;
- preserve machine-readable evidence; and
- turn a measured network profile into a parallelism hypothesis.

## What you will build

```text
rank 0 / GPU 0 ---- ordinary cluster network ---- rank 1 / GPU 0
       \                                           /
        \--------- ordinary network --------------/
                         rank 2 / GPU 0

message sizes: 1 KiB -> 64 KiB -> 1 MiB -> 16 MiB
operations:    ping-pong, all-reduce, all-to-all
outputs:       correctness + per-rank samples + NCCL transport logs
```

`src/nccl_benchmark.py` runs the operations. `src/analyze_results.py` extracts
rank-0 structured records from Pod logs and writes `artifacts/results.json` and
`artifacts/report.md`.

## Files in this lesson

```text
27-nccl-network-characterization/
├── README.md
├── src/
│   ├── nccl_benchmark.py
│   └── analyze_results.py
├── fixtures/
│   └── sample-rank0.txt
├── k8s/
│   └── network-benchmark.yaml.tpl
└── scripts/
    ├── render.py
    ├── deploy.sh
    ├── observe.sh
    └── test-analyzer.sh
```

The container image must provide Python, CUDA-enabled PyTorch, and NCCL. It is
passed as a full digest reference; no mutable image tag is committed.

## Concepts and mental model

NCCL implements GPU-oriented collective and point-to-point communication. In
PyTorch, the application calls `torch.distributed`; the process group delegates
CUDA tensor communication to NCCL.

Think in layers:

```text
application operation (all_reduce)
  -> PyTorch process group
  -> NCCL collective algorithm and protocol
  -> CUDA buffers / GPU DMA path
  -> network transport selected by installed stack
  -> Pod veth / host interface / VPC path
```

An NCCL `INFO` line naming `Socket` is evidence of socket transport. An
available EFA device by itself is not proof NCCL used AWS OFI NCCL. Conversely,
ordinary G-series nodes can still communicate correctly with sockets; they may
simply expose network cost more clearly.

**Latency** is elapsed time for an operation. **Payload rate** divides the
declared tensor payload by time. It excludes protocol overhead and may under-
or over-represent hardware traffic depending on the collective.

For an all-reduce, tools often report an algorithm bandwidth:

```text
algbw = message_bytes / seconds
```

and an approximate bus bandwidth correction:

```text
busbw = algbw × 2 × (ranks - 1) / ranks
```

This is a reporting convention for comparison, not direct NIC telemetry.

## Under the hood

### Point-to-point round trip

Rank 0 sends a tensor to rank 1. Rank 1 sends it back. Rank 2 waits at group
barriers but does not carry the payload:

```text
rank 0 --N bytes--> rank 1
rank 0 <--N bytes-- rank 1
```

The measured duration is a round trip and the reported logical payload is
`2N`. It must not be labelled one-way latency.

### All-reduce

Every rank begins with a rank marker. A sum all-reduce leaves every element
equal to `1 + 2 + 3 = 6`. The implementation may use a ring, tree, or other
algorithm, selected by NCCL from message size and topology. Do not infer the
algorithm from a generic diagram; keep the NCCL log.

### All-to-all

Each rank splits its input into one chunk per destination. After
`all_to_all_single`, rank `d` receives one chunk from every source. This
communication pattern matters for expert parallelism. On an ordinary network,
many peer exchanges can create a different bottleneck from all-reduce.

The program places barriers immediately before timing so one rank's early start
does not dominate. Barriers are excluded from the timed interval, but operation
completion still includes synchronization implied by the collective. CUDA is
synchronized before reading the clock.

## Prerequisites and preflight

Set the guarded target:

```bash
cd lessons/phase-04-distributed/27-nccl-network-characterization
export AWS_REGION='REPLACE_WITH_REGION'
export EKS_CLUSTER='REPLACE_WITH_CLUSTER'
export GPU_NODEGROUP='REPLACE_WITH_LAB_GPU_NODEGROUP'
export CONFIRM_GPU_NODEGROUP="$GPU_NODEGROUP"
export LAB_NAMESPACE='oms-distributed-27'
../common/scripts/assert-eks-target.sh
```

Resolve and review a CUDA PyTorch image:

```bash
export PYTORCH_IMAGE='registry/repository@sha256:64_lowercase_hex_characters'
```

Record:

```text
image digest:
PyTorch version:
CUDA runtime version:
NCCL version:
GPU driver:
instance type:
availability zones:
EFA device/plugin/provider present?:
```

The core path assumes only sockets. If EFA is present, run it as a separate
labelled experiment after proving the socket baseline; never mix the two in one
result.

Run the free analyzer fixture:

```bash
chmod +x scripts/*.sh scripts/*.py src/*.py
./scripts/test-analyzer.sh
```

## Cost and safety

Use a maximum of 120 GPU-minutes unless you explicitly approve more. The
benchmark's largest default tensor is 16 MiB—large enough to reveal payload
effects without intentionally exhausting VRAM. Do not jump to GiB-sized
allocations.

No public endpoint, PVC, host network, privileged container, or host path is
used. NCCL opens Pod-to-Pod connections inside the cluster network. Network
policies or security groups must permit the selected path; do not solve a
connectivity failure by opening broad public ingress.

Stop when:

- the three Pods are not on three distinct selected nodes;
- the image or node driver cannot initialize CUDA;
- NCCL logs reveal a transport different from the experiment label;
- correctness fails at any size;
- a benchmark exceeds its process-group timeout; or
- the GPU budget reaches its limit.

## Predict before running

1. Which size is more dominated by fixed startup latency: 1 KiB or 16 MiB?
2. Does doubling message bytes guarantee doubled duration?
3. Why is point-to-point round-trip payload `2N`?
4. Which operation resembles expert routing?
5. Which evidence proves socket versus RDMA transport?
6. Why can all ranks show low GPU utilization while waiting for a collective?

## Lab outline

1. Validate the analyzer using committed fake logs.
2. scale to exactly three one-GPU nodes.
3. deploy one NCCL rank per node.
4. run the correctness-first message-size sweep.
5. retain NCCL INFO transport logs and placement.
6. change only message size.
7. diagnose a deliberately broken network-interface selection.
8. clean up and restore idle capacity.

## Step-by-step lab

### 1. Test analysis without GPUs

```bash
./scripts/test-analyzer.sh
python -m json.tool artifacts/fixture-results.json
```

Expected: three fixture records and `correctness.passed: true`. The fixture
numbers are synthetic and carry `fixture: true`; never mix them with measured
results.

### 2. Start bounded capacity

```bash
export I_UNDERSTAND_GPU_COSTS=yes
../common/scripts/scale-three-nodes.sh up
kubectl get nodes -o json |
  ../common/scripts/verify-three-gpu-nodes.py \
    --nodegroup "$GPU_NODEGROUP"
../common/scripts/capture-topology.sh
```

### 3. Render and deploy

```bash
./scripts/render.py
./scripts/deploy.sh
```

The StatefulSet uses ordinals 0–2 as ranks and required hostname anti-affinity.
Each process logs version information before the first benchmark.

### 4. Observe placement and raw transport logs

```bash
./scripts/observe.sh
grep -Ei 'NCCL|NET/|Socket|IB|OFI' artifacts/logs/rank-*.log \
  >artifacts/nccl-transport-lines.txt
```

Read the lines rather than searching for only the word you hope to see. Record
the interface and transport actually selected.

### 5. Analyze

```bash
python src/analyze_results.py \
  --logs artifacts/logs \
  --output artifacts/results.json \
  --report artifacts/report.md
python -m json.tool artifacts/results.json
```

The result includes one record for each operation/size pair. A passing result
requires every reported correctness flag.

### 6. Interpret size regions

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/results.json").read_text())
for row in d["measurements"]["records"]:
    print(
        row["operation"],
        row["message_bytes"],
        round(row["median_ms"], 3),
        round(row["payload_gbps"], 3),
    )
PY
```

Do not publish a single “network speed.” Publish the curve, operation,
participant count, statistic, software stack, and topology.

## Inspect what happened

```bash
kubectl -n "$LAB_NAMESPACE" get pods -o wide
kubectl -n "$LAB_NAMESPACE" describe pods
kubectl -n "$LAB_NAMESPACE" get endpoints network-benchmark
kubectl -n "$LAB_NAMESPACE" exec network-benchmark-0 -- nvidia-smi topo -m
kubectl -n "$LAB_NAMESPACE" exec network-benchmark-0 -- \
  python -c 'import torch; print(torch.__version__, torch.version.cuda)'
```

`nvidia-smi topo -m` is local-host topology. With one visible GPU per Pod it
cannot describe the inter-node network. Join it with node instance types,
zones, Pod placement, and NCCL network logs.

## Deliberate failure

Render a copy and force a nonexistent interface:

```bash
cp artifacts/network-benchmark.yaml \
  artifacts/network-benchmark-bad-iface.yaml
python3 - <<'PY'
from pathlib import Path

p = Path("artifacts/network-benchmark-bad-iface.yaml")
text = p.read_text()
needle = "            - name: NCCL_DEBUG_SUBSYS\n              value: INIT,NET,GRAPH,COLL\n"
replacement = needle + (
    "            - name: NCCL_SOCKET_IFNAME\n"
    "              value: =definitely-not-an-interface\n"
)
if needle not in text:
    raise SystemExit("expected environment block not found")
p.write_text(text.replace(needle, replacement))
PY
kubectl apply -f artifacts/network-benchmark-bad-iface.yaml
kubectl -n "$LAB_NAMESPACE" rollout restart statefulset/network-benchmark
```

Expect initialization failure or timeout, not a valid benchmark. Capture every
rank log and events. Diagnose from the NCCL interface-selection message. Repair
by reapplying `artifacts/network-benchmark.yaml`.

## Controlled experiment

The default run changes only `message_bytes`. World size, operation
implementation, image, nodes, dtype, iterations, and synchronization remain
fixed. Within each operation, plot median milliseconds and payload Gbit/s by
size. Do not compare operation curves as if their byte semantics were equal.

Optional second experiment: set `BENCHMARK_WORLD_SIZE=2` only after changing
the StatefulSet to two replicas and documenting that rank count also changes
collective algorithms and bus-bandwidth correction.

## Verification

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/results.json").read_text())
assert d["correctness"]["passed"] is True
operations = {r["operation"] for r in d["measurements"]["records"]}
assert operations == {"all-reduce", "all-to-all", "ping-pong"}
assert len({r["message_bytes"] for r in d["measurements"]["records"]}) >= 4
assert d["environment"]["world_size"] == 3
print("network characterization contract: PASS")
PY
```

## Expected result

All correctness checks pass for all sizes. Small messages usually show low
payload rate because fixed overhead dominates; larger messages often improve
payload rate until another limit appears. That qualitative expectation is not
a throughput claim. Your measured numbers may vary with instance size, zones,
placement, congestion, image, driver, NCCL version, and transport.

## Troubleshooting

| Layer | Symptom | Evidence |
|---|---|---|
| scheduling | rank Pod Pending | events, node affinity, anti-affinity, GPU capacity |
| rendezvous | ranks wait before NCCL version log | Service DNS/endpoints and port |
| CUDA | `no GPUs found` | Pod resources, device plugin, `nvidia-smi` |
| transport | no usable interface | NCCL INFO logs and Pod interfaces |
| collective | one size hangs | last structured event from every rank |
| correctness | wrong markers | source/destination chunk formula and dtype |
| analysis | missing records | raw rank-0 log and `BENCHMARK_RESULT` count |
| interpretation | impossible Gbit/s | units, round-trip factor, timing statistic |

## Evidence to collect

- topology files from the shared helper
- `artifacts/logs/rank-0.log` through `rank-2.log`
- `artifacts/nccl-transport-lines.txt`
- `artifacts/results.json`
- `artifacts/report.md`
- Pod placement, events, image IDs, driver/CUDA/NCCL versions
- failure logs for the nonexistent interface

Sanitize internal IPs and cluster/node names before publishing. Do not remove
software versions or topology facts needed for reproducibility.

## Knowledge check

1. What does `algbw` divide, and what does it omit?
2. Why is the all-reduce bus correction a convention rather than NIC telemetry?
3. Which evidence proves the selected NCCL transport?
4. Why might TP decode suffer even when large-message payload rate looks good?
5. What makes all-to-all different from all-reduce?
6. Why must correctness gate performance reporting?

## Exercises

Guided: add a 4 MiB message size and verify the analyzer preserves sorted byte
order.

Independent: repeat the experiment in same-zone and explicitly multi-zone
placements if your organization permits both. Change only placement, record the
actual zones, and avoid generalizing from one run.

<details>
<summary>Solution outline</summary>

Add `4194304` to `--sizes`. For the topology experiment, use separate node
groups or approved placement constraints; never mutate production subnets or
zones for a lesson. Repeat runs and report distributions, not only best values.

</details>

## Completion gate

You pass when every operation is correct, at least four sizes are measured,
transport selection is supported by logs, the rank-to-node map proves three
hosts, and your report distinguishes latency, payload rate, bus convention, and
wire rate. Include one failure diagnosis and a hypothesis for TP versus PP.

## Cleanup

```bash
../common/scripts/cleanup-namespace.sh
../common/scripts/scale-three-nodes.sh down
```

Prove namespace absence, baseline scaling restoration, no selected nodes, and
no unexpected load balancer or volume. Preserve sanitized result files outside
the cluster.

## Primary references

Required, reviewed 2026-10-21:

- [NCCL user guide](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
- [NCCL environment variables](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)
- [NCCL tests performance calculations](https://github.com/NVIDIA/nccl-tests/blob/master/doc/PERFORMANCE.md)
- [PyTorch distributed collectives](https://docs.pytorch.org/docs/stable/distributed.html)
- [AWS EC2 accelerated-computing networking](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)

The official NCCL documentation displayed release 2.32.3 when reviewed. The lab
does not require that exact library; it records the version bundled into the
learner's immutable image and treats version changes as experiment changes.
