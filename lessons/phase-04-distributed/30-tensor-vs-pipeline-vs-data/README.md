# 30 — Tensor vs pipeline vs data parallelism

**Status:** draft
**Estimated time:** 1–2 days
**Compute profile:** three separate one-GPU EKS nodes, used sequentially for
DP=3, TP=3, and PP=3
**Estimated GPU-minutes:** 180–360 under a fixed approved budget
**Estimated cloud cost:** three GPU nodes for three carefully bounded layouts,
three node-local model caches, normal EKS/network charges, and model egress;
calculate using current Regional pricing
**Prerequisites:** lessons 12, 13, and 24–29
**Last validated:** 2026-10-21
**Validated with:** Python 3.9 syntax, fixture comparison tests, Bash syntax,
and static manifest review; no live vLLM/Ray/GPU comparison has been run

## Why this matters

Data, tensor, and pipeline parallelism solve different constraints:

- DP provides more complete replicas when the model already fits one GPU.
- TP makes one layer span GPUs and communicates repeatedly inside the model.
- PP divides layer ranges and transfers activations between stages.

Comparing them requires discipline. If DP uses a shorter prompt, TP uses a
different quantization, or PP runs on different nodes, the numbers do not answer
the strategy question. This lesson freezes model revision, image digest,
request bytes, context limit, concurrency, nodes, and measurement method.

The chosen smoke model has dimensions divisible by three and fits one GPU, so
all strategies are mechanically possible. The goal is not to crown a universal
winner. It is to connect observed latency, throughput, GPU memory, network
behavior, and failure domain to each architecture.

## Learning outcomes

By the end, you can:

- map one request through DP=3, TP=3, and PP=3;
- distinguish throughput replication from model-capacity scaling;
- identify where each strategy communicates;
- explain why TP is sensitive to ordinary inter-node latency;
- explain PP bubbles and stage imbalance;
- explain why DP has three independent failure domains;
- build a controlled experiment with a shared workload fingerprint;
- deploy all three layouts sequentially on the same node group;
- capture correctness, latency, throughput, GPU, network, and placement
  evidence;
- reject incompatible TP dimensions before provisioning; and
- write a recommendation tied to model fit and workload rather than GPU count.

## What you will build

```text
DP=3
router -> [full model GPU A]
       -> [full model GPU B]
       -> [full model GPU C]

TP=3
request -> layer shards A <all-reduce> B <all-reduce> C -> response

PP=3
request -> layers on A -> activation -> layers on B
        -> activation -> layers on C -> response
```

Two rendered manifests implement the layouts:

- a three-replica vLLM Deployment for DP;
- a three-GPU RayCluster used for TP or PP.

`compare_results.py` refuses results with different model revisions, image
digests, or workload fingerprints.

## Files in this lesson

```text
30-tensor-vs-pipeline-vs-data/
├── README.md
├── decision-template.md
├── profiles/comparison.env.example
├── requests/completion.json
├── inputs/incompatible-config.json
├── fixtures/{dp,tp,pp}.json
├── src/
│   ├── download_model.py
│   ├── benchmark_client.py
│   ├── compare_results.py
│   └── check_tp_shape.py
├── k8s/
│   ├── dp.yaml.tpl
│   └── ray-model-parallel.yaml.tpl
└── scripts/
    ├── render.py
    ├── deploy-strategy.sh
    ├── start-ray-server.sh
    ├── benchmark.sh
    ├── observe.sh
    └── test-comparison.sh
```

## Concepts and mental model

### DP: capacity for requests

Each DP replica loads the entire model. A ClusterIP Service distributes
connections among Ready Pods. Independent requests do not exchange model
tensors. With enough concurrent work, three replicas can process different
requests simultaneously. A single request still uses one GPU.

### TP: capacity for layers

Each TP rank holds slices of many layer matrices. Intermediate values need
collectives such as all-reduce or all-gather. One request uses all three GPUs.
Small autoregressive decode steps can trigger many small synchronization points,
which is a poor match for high-latency node-to-node paths.

### PP: capacity for layer stacks

Each PP rank holds full layers for one stage. One request flows through all
stages. Boundary activations cross the network. Multiple requests can occupy
different stages, but low concurrency leaves fill/drain bubbles. The slowest
stage determines steady-state progress.

### Failure domains

With DP, losing one replica reduces capacity while other replicas may remain
healthy. With TP or PP, losing any participating rank normally invalidates the
whole distributed engine. Kubernetes can replace a Pod, but application
process groups and model actors usually need coordinated restart.

## Under the hood

The shared profile uses an exact model revision with hidden size 768, 12
attention heads, and 12 transformer layers:

```text
768 % 3 = 0
12 heads % 3 = 0
12 layers / 3 = 4 per PP stage
```

That makes `TP=3` and `PP=3` straightforward for a teaching comparison. A
different model must pass `check_tp_shape.py` and current vLLM architecture
support checks.

For DP, Kubernetes owns three server processes. The Service is the request
router. For TP/PP, KubeRay owns one GPU-visible head and two GPU workers; vLLM
uses Ray to create the model execution world.

All model Pods run as non-root UID/GID 1000 and set `fsGroup: 1000` so their
node-local `emptyDir` model caches are writable. This keeps filesystem
permission failures separate from engine or distributed-runtime failures.

The benchmark hashes the exact JSON request bytes. Its result records:

```text
model ID + model revision + image digest + live vLLM/Ray versions
+ workload SHA-256
+ strategy + request count + concurrency
+ success count + wall time + end-to-end latency samples
```

Before recording, the wrapper reads the installed package versions from a
serving Pod and requires the declared exact versions. The comparator rejects
mismatches before computing ratios. Ratios are shown as observations, not
predictions or universal claims.

## Prerequisites and preflight

```bash
cd lessons/phase-04-distributed/30-tensor-vs-pipeline-vs-data
chmod +x scripts/*.sh scripts/*.py src/*.py
./scripts/test-comparison.sh
source profiles/comparison.env.example
```

Set guarded infrastructure and immutable image:

```bash
export AWS_REGION='REPLACE_WITH_REGION'
export EKS_CLUSTER='REPLACE_WITH_CLUSTER'
export GPU_NODEGROUP='REPLACE_WITH_LAB_GPU_NODEGROUP'
export CONFIRM_GPU_NODEGROUP="$GPU_NODEGROUP"
export LAB_NAMESPACE='oms-distributed-30'
export VLLM_IMAGE='vllm/vllm-openai@sha256:64_lowercase_hex_characters'
../common/scripts/assert-eks-target.sh
```

Verify the model configuration:

```bash
python3 src/check_tp_shape.py \
  --config inputs/incompatible-config.json \
  --tp 3 || true
```

That fixture must fail. For the real exact snapshot, download `config.json` and
run the same command before GPU startup.

## Cost and safety

Scale GPU capacity once, then run layouts sequentially. Delete one layout before
starting the next so stale servers do not consume GPUs or receive traffic.
Record a hard wall-clock deadline.

The manifests require:

- one GPU per Pod;
- three distinct hostnames;
- exact node-group affinity;
- digest-pinned images;
- exact model revision;
- node-local bounded caches; and
- only ClusterIP Services.

Stop if a result has request failures, different fingerprints, different node
sets, an unexpected transport, or budget exhaustion. Never expose the
unauthenticated teaching API publicly.

## Predict before running

1. Which strategy can keep serving after one rank disappears?
2. Which strategy stores full weights three times?
3. Which strategy communicates within many layers?
4. Which strategy sends activations across stage boundaries?
5. Why might DP have best aggregate throughput but fail to fit a larger model?
6. Why must the workload fingerprint match?

## Lab outline

1. Validate comparison fixtures and TP shape checks.
2. scale exactly three nodes.
3. render both deployment forms.
4. run DP, TP, and PP sequentially.
5. verify identical request/model/image inputs.
6. collect GPU, network, and failure evidence.
7. compare results and write a decision.
8. clean up and restore capacity.

## Step-by-step lab

### 1. Validate the harness

```bash
./scripts/test-comparison.sh
python3 -m json.tool artifacts/fixture-comparison.json
```

Fixture results are synthetic and marked as such. This proves mismatch checks
and report generation, not performance.

### 2. Prepare capacity and manifests

```bash
export I_UNDERSTAND_GPU_COSTS=yes
../common/scripts/scale-three-nodes.sh up
kubectl get nodes -o json |
  ../common/scripts/verify-three-gpu-nodes.py \
    --nodegroup "$GPU_NODEGROUP"
./scripts/render.py
```

Inspect all GPU requests and ensure no `LoadBalancer` appears.

### 3. Run DP=3

```bash
export STRATEGY='data-parallel'
./scripts/deploy-strategy.sh
./scripts/benchmark.sh
./scripts/observe.sh
cp artifacts/latest-result.json artifacts/raw/dp.json
../common/scripts/cleanup-namespace.sh
```

DP launches three independent vLLM servers. The benchmark sends enough
requests for the Service to have an opportunity to use all Ready endpoints.
Confirm actual Pod logs, rather than assuming perfect load distribution.

### 4. Run TP=3

```bash
export STRATEGY='tensor-parallel'
./scripts/deploy-strategy.sh
./scripts/start-ray-server.sh
./scripts/benchmark.sh
./scripts/observe.sh
cp artifacts/latest-result.json artifacts/raw/tp.json
../common/scripts/cleanup-namespace.sh
```

Capture NCCL lines. With three separate nodes, expect transport and collective
cost to be visible. Do not increase timeouts before understanding stalls.

### 5. Run PP=3

```bash
export STRATEGY='pipeline-parallel'
./scripts/deploy-strategy.sh
./scripts/start-ray-server.sh
./scripts/benchmark.sh
./scripts/observe.sh
cp artifacts/latest-result.json artifacts/raw/pp.json
```

The same three Ray Pods are used, but vLLM launch factors change from
`TP=3,PP=1` to `TP=1,PP=3`.

### 6. Compare

```bash
python3 src/compare_results.py \
  --dp artifacts/raw/dp.json \
  --tp artifacts/raw/tp.json \
  --pp artifacts/raw/pp.json \
  --output artifacts/comparison.json \
  --report artifacts/comparison.md
```

If the comparator rejects, fix experimental consistency; do not bypass the
check.

## Inspect what happened

For every layout, retain:

```bash
kubectl -n "$LAB_NAMESPACE" get pods,endpoints -o wide
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp
kubectl -n "$LAB_NAMESPACE" top pods 2>/dev/null || true
```

For TP/PP also retain Ray status and vLLM logs. For DP, count requests in each
replica's logs. Join latency results with GPU memory/utilization and lesson-27
network curves.

## Deliberate failure

Use the incompatible config:

```bash
set +e
python3 src/check_tp_shape.py \
  --config inputs/incompatible-config.json \
  --tp 3 \
  --output artifacts/incompatible-tp.json
status=$?
set -e
test "$status" -eq 2
```

Hidden size 4096 and 32 attention heads do not divide by three. This failure
must happen locally before model download or GPU allocation. Repair by choosing
a compatible model or a supported TP degree—not by rounding tensor shapes.

## Controlled experiment

The strategy is the controlled variable. Hold fixed:

- node identities and instance types;
- image digest and software versions;
- model ID/revision and quantization;
- request file bytes;
- context and maximum tokens;
- request count/concurrency;
- warm-up count and measurement client; and
- transport configuration.

If a strategy requires changing one of those, mark the result non-comparable
and explain why.

## Verification

```bash
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/comparison.json").read_text())
assert d["correctness"]["passed"] is True
assert set(d["measurements"]["strategies"]) == {
    "data-parallel", "tensor-parallel", "pipeline-parallel"
}
assert len(set(d["environment"]["workload_fingerprints"])) == 1
assert len(set(d["environment"]["model_revisions"])) == 1
assert len(set(d["environment"]["image_digests"])) == 1
print("controlled strategy comparison: PASS")
PY
```

## Expected result

All layouts return valid completions. Exact ordering is not predicted. DP may
use concurrent replicas effectively; TP may show high communication sensitivity;
PP may show bubbles at low concurrency. Any opposite result is acceptable when
supported by evidence. The large-model lesson remains PP-focused because DP
cannot make a model fit and TP=3 may be invalid or network-heavy.

## Troubleshooting

| Layer | Symptom | Diagnostic |
|---|---|---|
| input | comparator mismatch | model/revision/image/workload fields |
| scheduling | fewer than three hosts | events, anti-affinity, GPU capacity |
| DP routing | one replica gets all work | endpoints, keep-alive behavior, Pod logs |
| TP | startup/collective timeout | divisibility, Ray resources, NCCL logs |
| PP | uneven utilization | stage map, bubbles, concurrency, memory |
| API | different output schema | exact vLLM version and request endpoint |
| benchmark | surprising ratio | raw samples, warm-up, failures, node consistency |

## Evidence to collect

- rendered manifests and exact profile
- `artifacts/raw/{dp,tp,pp}.json`
- per-layout Pod/node map and image IDs
- per-layout model provenance and vLLM logs
- NCCL/network evidence for TP and PP
- per-replica logs for DP
- `artifacts/comparison.json`
- `artifacts/comparison.md`
- completed `decision-template.md`

Sanitize infrastructure identifiers but preserve experiment fingerprints.

## Knowledge check

1. Why does DP scale requests but not model capacity?
2. Why is TP sensitive to inter-node latency?
3. What creates PP bubbles?
4. Why is rank loss a larger failure for model-parallel layouts?
5. Which inputs must match for comparison?
6. When should you reject all three layouts and choose different hardware?

## Exercises

Guided: rerun only PP with concurrency 1 and 4. Explain bubble/utilization and
KV-memory changes.

Independent: design a hybrid `DP=2, PP=3` layout for six GPUs. Draw groups,
calculate copies/shards, state routing behavior, and list new failure domains.

<details>
<summary>Solution outline</summary>

The hybrid has two independent three-stage pipelines: ranks 0–2 and 3–5. A
router selects a pipeline. Each pipeline fails if any of its three stages
fails; the other pipeline may continue. Model weights are stored once per stage
per replica, so there are two complete distributed copies.

</details>

## Completion gate

You pass when all three behavioral checks succeed, comparison fields match,
every layout maps to three nodes, and your decision explains model fit,
communication, latency/throughput, memory, and failure behavior. A strategy
failure is acceptable only when diagnosed and reported without fabricated
metrics.

## Cleanup

```bash
../common/scripts/cleanup-namespace.sh
../common/scripts/scale-three-nodes.sh down
```

Verify no DP Deployment, RayCluster, Service, Pod, cache, volume, or load
balancer remains and node-group scaling equals the saved baseline.

## Primary references

Required, reviewed 2026-10-21:

- [vLLM parallelism and scaling](https://docs.vllm.ai/en/latest/serving/parallelism_scaling/)
- [vLLM distributed serving](https://docs.vllm.ai/en/latest/serving/distributed_serving/)
- [PyTorch tensor parallel](https://docs.pytorch.org/docs/stable/distributed.tensor.parallel.html)
- [PyTorch pipelining](https://docs.pytorch.org/docs/stable/distributed.pipelining.html)
- [Megatron-LM paper](https://arxiv.org/abs/1909.08053)
- [GPipe paper](https://arxiv.org/abs/1811.06965)

Use the exact versions and digests recorded by the experiment. This draft's
teaching targets remain vLLM 0.28.0, Ray 2.59.0, and KubeRay 1.7.0.
