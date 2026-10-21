# 23 — Capstone: optimize under an SLO

**Status:** draft
**Estimated time:** 1–3 days
**Compute profile:** required `local-cpu`; practical capstone uses one EKS
NVIDIA GPU node with at least 24 GiB VRAM, one GPU Pod, and private port-forward
access
**Estimated GPU-minutes:** 0 for the selection tutorial; maximum 120 for the
default real capstone, including repeats and failure drill
**Estimated cloud cost:** one GPU node for no more than two hours, model/image
download and storage, plus standing EKS, NAT, public IPv4, and other account
costs. Price the exact instance/Region on the execution date and include existing
standing costs.
**Prerequisites:** lessons 00–22, especially 10, 12, 13, and 17–22; Python 3.9+,
AWS CLI, `kubectl`, Docker Buildx for digest resolution, a working private EKS
GPU cluster/device plugin, and permission to create one namespaced Deployment
**Last validated:** 2026-10-21
**Validated with:** dependency-free benchmark/selection/render Python syntax,
JSON/static validation, and synthetic hard-gate tests. This workspace did not
have access to the learner's EKS GPU and therefore did not execute the
Deployment, image pull, vLLM server, benchmark, or GPU teardown. Status remains
`draft` until clean hardware runs and independent review.

## Why this matters

Real optimization is constrained:

```text
meet correctness + quality + reliability + latency + memory + cost
then maximize the chosen objective
```

The fastest row is useless if it times out, changes outputs, exceeds 24 GiB, or
only wins because it generated fewer tokens. This capstone integrates the
phase's mechanisms into a reproducible Kubernetes experiment:

- immutable engine image and model commit;
- one fixed workload and quality gate;
- three bounded candidate configurations;
- private one-GPU Deployment;
- streaming per-request TTFT/e2e records;
- GPU time-series evidence;
- hard-gate selection before throughput ranking;
- repeatability, ablation, failure/repair, and verified cleanup.

## Learning outcomes

By the end, you can:

- translate an application requirement into machine-checkable SLO/quality/cost
  gates;
- audit a bounded candidate matrix and identify coupled changes;
- render and inspect a digest-pinned one-GPU Kubernetes Deployment;
- deploy, port-forward, smoke-test, benchmark, observe, break, repair, and delete
  the service;
- produce `oms-benchmark/v1` raw per-request evidence;
- calculate success, quality, TTFT/e2e, output throughput, and peak VRAM;
- reject an attractive but infeasible candidate;
- repeat the winner and a close alternative;
- explain the result through scheduler, KV, graph, and prefix mechanisms;
- deliver a report another learner can reproduce or falsify.

## What you will build

```mermaid
flowchart LR
    C[candidates.json] --> R[render_manifest.py]
    I[image@sha256] --> R
    R --> K[EKS Deployment: 1 GPU]
    W[workload.json] --> B[streaming benchmark]
    K --> B
    B --> RAW[per-request results]
    K --> OBS[logs/events/GPU series]
    RAW --> A[assemble measured set]
    OBS --> A
    S[SLO gates] --> SEL[select_candidate.py]
    A --> SEL
    SEL --> REP[report + rollback decision]
```

The Service is `ClusterIP`; access uses authenticated `kubectl port-forward`.
There is no public load balancer or API authentication layer.

## Files in this lesson

```text
23-capstone-optimize-under-slo/
├── README.md
├── report-template.md
├── results.schema.json
├── configs/
│   ├── candidates.json
│   ├── slo.json
│   └── workload.json
├── fixtures/
│   └── candidate-results.synthetic.json
├── scripts/
│   ├── assemble-measured-results.py
│   ├── benchmark.sh
│   ├── cleanup.sh
│   ├── collect-cluster-evidence.sh
│   ├── deploy.sh
│   ├── failure-drill.sh
│   ├── preflight.sh
│   ├── render-deployment.sh
│   ├── resolve-vllm-image.sh
│   ├── run-cpu-lab.sh
│   ├── sample-gpu.sh
│   └── verify-results.py
├── solutions/SOLUTIONS.md
└── src/
    ├── benchmark_endpoint.py
    ├── render_manifest.py
    └── select_candidate.py
```

Rendered manifests and results go under ignored `artifacts/`; committed YAML
does not contain an account, cluster, registry credential, or mutable image tag.

## Concepts and mental model

### Hard constraints before objective

The committed SLO requires:

```text
success rate                 >= 0.99
quality pass rate            >= 0.95
p95 TTFT                     <= 2500 ms
p95 end-to-end               <= 8000 ms
output throughput            >= 1 token/s
peak GPU memory              <= 23 GiB
total experiment             <= 120 GPU-minutes
```

Among feasible candidates, choose highest output-token throughput. These values
are a teaching contract, not a universal production SLO. Review/freeze them
before seeing results.

### Why output-token throughput

Request throughput can be gamed by shorter answers. Output tokens per wall
second still needs output-length and quality checks, but better represents
autoregressive work than requests/s alone. Always publish both.

### Candidate treatments

- `b0-eager-small`: transparent eager baseline with conservative scheduler.
- `c1-graphs-capacity`: graph-enabled treatment and larger scheduler capacity.
- `c2-prefix-cache`: prefix-reuse treatment for the shared-prefix workload.

The candidates intentionally represent **treatments**, not perfect one-factor
isolations. Lessons 17–22 provide individual ablations. The capstone asks which
operational configuration wins, then requires ablation to explain it.

### Measurement lifecycle

```text
cold deployment/startup
-> health ready
-> declared warmup (excluded)
-> measured steady state (included)
-> evidence snapshot/time series
-> stop/reconfigure
```

Never mix image pull/model download/graph capture with steady-state percentiles
unless cold-start latency is the stated objective.

### Percentiles and samples

The client uses linear-interpolated sample percentiles and retains each request.
Twenty-four requests are enough for a teaching smoke comparison, not a strong
production tail claim. A p95 with 24 points is determined by the slowest few
samples and has wide uncertainty. Repeat and increase sample size within budget.

### Concurrency and streaming

The dependency-free client uses a thread pool for closed-loop concurrency. It
records:

- send-to-first-content TTFT from SSE;
- full end-to-end duration;
- HTTP/error;
- input/output tokens when server usage is present;
- output SHA-256 instead of storing model text;
- prompt-specific substring quality pass.

For rigorous capacity, supplement with lesson 12's calibrated open-loop load.

## Under the hood

### Kubernetes path

```text
render exact candidate
-> Namespace oms-lesson-23
-> Deployment/vllm (Recreate, one replica)
-> scheduler finds node with nvidia.com/gpu=1
-> device plugin/runtime exposes GPU
-> image digest pulled
-> pinned model revision downloaded
-> vLLM allocates weights/KV/graphs
-> startup probe /health
-> readiness adds Pod IP to Service endpoints
-> port-forward tunnels localhost:8000 to ClusterIP service
```

`Deployment/vllm` is reused between candidates. `Recreate` releases the single
GPU before creating the next Pod. Candidate labels and exact args change in the
rendered manifest.

### Benchmark path

```text
main thread builds fixed tasks
-> ThreadPoolExecutor maintains concurrency
-> each task POSTs stream=true
-> first nonempty content chunk timestamps TTFT
-> [DONE] timestamps completion
-> usage supplies token counts
-> quality predicate checks required substring
-> raw request retained
-> summary computed over successes, with success rate over all requests
```

Failed requests are never silently dropped from success/quality rates.

### GPU peak

One `nvidia-smi` snapshot is not a peak. `sample-gpu.sh` polls inside the Pod.
For stronger evidence use the cluster's approved DCGM/Prometheus time series.
Record sampling interval and calculate peak MiB/1024 from the interval covering
the benchmark. Supply that value explicitly to the assembler.

### Selection

`assemble-measured-results.py` converts raw benchmark summaries plus measured
peak GiB into a candidate set. `select_candidate.py` applies every hard gate,
then ranks feasible rows by the declared objective. It keeps failed-gate names.

## Prerequisites and preflight

### Free path

```bash
cd lessons/phase-03-optimization/23-capstone-optimize-under-slo
chmod +x scripts/*.sh scripts/*.py src/*.py
./scripts/preflight.sh
mkdir -p artifacts
cp report-template.md artifacts/report.md
```

Expected:

```text
python: 3.x.y
lesson 23 preflight passed
```

### EKS path

Set non-secret identifiers:

```bash
export AWS_REGION=replace-with-region
export EKS_CLUSTER=replace-with-lab-cluster
export GPU_NODEGROUP=replace-with-lab-gpu-nodegroup
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER"
export CONFIRM_LAB_CONTEXT="$(kubectl config current-context)"
export CONFIRM_GPU_NODEGROUP="$GPU_NODEGROUP"
printf 'region=%s cluster=%s nodegroup=%s context=%s\n' \
  "$AWS_REGION" "$EKS_CLUSTER" "$GPU_NODEGROUP" "$CONFIRM_LAB_CONTEXT"
```

Do not paste account IDs/endpoints into committed files. Record identity/state
in ignored evidence:

```bash
aws sts get-caller-identity | tee artifacts/aws-identity.json
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.{status:status,instanceTypes:instanceTypes,scaling:scalingConfig}' \
  --output json |
  tee artifacts/nodegroup-before.json

RUN_GPU_TRACK=1 ./scripts/preflight.sh
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,GPU:.status.allocatable.nvidia\\.com/gpu
```

Resolve immutable image:

```bash
export VLLM_IMAGE_TAG=vllm/vllm-openai:v0.28.0
export VLLM_IMAGE="$(./scripts/resolve-vllm-image.sh)"
printf '%s\n' "$VLLM_IMAGE" | tee artifacts/vllm-image-digest.txt
```

Inspect the version:

```bash
docker run --rm "$VLLM_IMAGE" --version | tee artifacts/vllm-version.txt
docker run --rm "$VLLM_IMAGE" --help > artifacts/vllm-help.txt
```

The benchmark wrapper also reads the installed `vllm` package version from the
running Pod and refuses to record a run when it differs from
`VLLM_EXPECTED_VERSION` (default `0.28.0`).

## Cost and safety

Before scaling:

```text
instance hourly price × planned 2 hours
+ standing EKS/NAT/public IPv4
+ EBS/cache/image transfer
= maximum authorized capstone cost
```

Guardrails:

- one namespace, one replica, one GPU request/limit;
- maximum 120 GPU-minutes across candidates;
- fixed candidate count; no unbounded sweep;
- `ClusterIP` plus port-forward only;
- public model pinned to exact commit; no model token required;
- engine image must match `@sha256`;
- no secrets in manifests/environment/report;
- no candidate runs concurrently;
- stop on other GPU workloads, unexpected public resource, OOM loop, or budget
  breach;
- record node-group scale-down before scaling up.

The generated Pod downloads model data. In a private subnet, NAT/data-processing
costs may apply. A production design should use reviewed cache/storage paths.

## Predict before running

1. Which synthetic candidate is fastest, and should it win?
2. Which candidate likely has the longest cold start?
3. How could graph memory affect the 23 GiB gate?
4. Why might prefix caching help only part of the workload?
5. What proves the Service routes to a ready Pod?
6. Why is a single post-run GPU snapshot insufficient?
7. Which resources remain chargeable after deleting only the Deployment?

## Lab outline

1. Run the free synthetic gate tutorial.
2. Freeze/hash SLO, workload, candidate matrix, image, model, and hardware.
3. Render/dry-run the baseline manifest.
4. Scale at most one GPU node if required; deploy and verify behavior.
5. Benchmark and collect logs/events/GPU time series.
6. Repeat for bounded candidates, then assemble/select.
7. Repeat winner/close alternative and perform ablation.
8. Break Service routing, diagnose, repair, verify.
9. Delete namespace, restore capacity, and prove cleanup.

## Step-by-step lab

### 1. Learn the selector without a GPU

```bash
./scripts/run-cpu-lab.sh
python3 -m json.tool artifacts/results.json
```

Expected:

```text
b0-eager-small         feasible=False failed=ttft_p95_ms
c1-graphs-capacity     feasible=True  failed=-
c2-prefix-cache        feasible=False failed=success_rate
winner: c1-graphs-capacity
verified hard gates precede objective selection
```

These are fictional numbers and cannot appear in your measured report.

### 2. Freeze and hash the contract

```bash
if command -v sha256sum >/dev/null; then
  sha256sum configs/slo.json configs/workload.json configs/candidates.json |
    tee artifacts/contract-sha256.txt
else
  shasum -a 256 configs/slo.json configs/workload.json configs/candidates.json |
    tee artifacts/contract-sha256.txt
fi
```

Review every prompt and gate now. Do not change them after seeing a candidate.

### 3. Render and inspect the baseline

```bash
./scripts/render-deployment.sh b0-eager-small
sed -n '1,260p' artifacts/b0-eager-small.yaml
kubectl apply --dry-run=server -f artifacts/b0-eager-small.yaml
```

Confirm:

- exact image digest and model revision;
- one replica/GPU;
- `Recreate`;
- `ClusterIP`;
- loopback is used later;
- candidate args match JSON;
- no secrets/public service.

### 4. Scale only if required

Read the before-state and use your reviewed organization/account procedure to
set desired/min/max to at most one GPU node. This repository does not guess a
destructive account-specific command. Wait until allocatable GPU appears:

```bash
kubectl get nodes -w
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

Start the 120-GPU-minute external timer.

### 5. Deploy baseline

```bash
./scripts/deploy.sh b0-eager-small
kubectl get pods -n oms-lesson-23 -o wide
kubectl get endpoints vllm -n oms-lesson-23
kubectl logs -n oms-lesson-23 deployment/vllm |
  tee artifacts/b0-eager-small-startup.log
```

The endpoint list must contain the ready Pod IP before testing.

### 6. Port-forward and smoke test

Dedicated shell:

```bash
kubectl port-forward --address 127.0.0.1 \
  -n oms-lesson-23 service/vllm 8000:8000
```

Another shell:

```bash
curl --fail --silent http://127.0.0.1:8000/health
curl --fail --silent http://127.0.0.1:8000/v1/models |
  python3 -m json.tool
curl --fail --silent http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"oms-model","messages":[{"role":"user","content":"Reply BLUE"}],
       "temperature":0,"max_tokens":16}' |
  tee artifacts/b0-smoke.json |
  python3 -m json.tool
```

### 7. Benchmark with GPU sampling

Start sampling in a dedicated shell:

```bash
SAMPLES=90 INTERVAL_SECONDS=2 ./scripts/sample-gpu.sh b0-eager-small
```

While it samples:

```bash
./scripts/benchmark.sh b0-eager-small
./scripts/collect-cluster-evidence.sh b0-eager-small
```

Inspect every failure and quality miss:

```bash
python3 - <<'PY'
import json
p="artifacts/b0-eager-small/results.json"
d=json.load(open(p, encoding="utf-8"))
print(json.dumps(d["summary"], indent=2))
for r in d["requests"]:
    if r["status_code"] != 200 or not r["quality_pass"]:
        print(r)
PY
```

### 8. Run the remaining candidates sequentially

For each `c1-graphs-capacity`, `c2-prefix-cache`:

```bash
./scripts/render-deployment.sh CANDIDATE_ID
./scripts/deploy.sh CANDIDATE_ID
kubectl get endpoints vllm -n oms-lesson-23
# restart port-forward if the existing session ended
SAMPLES=90 INTERVAL_SECONDS=2 ./scripts/sample-gpu.sh CANDIDATE_ID
./scripts/benchmark.sh CANDIDATE_ID
./scripts/collect-cluster-evidence.sh CANDIDATE_ID
```

Replace `CANDIDATE_ID` literally with one reviewed ID. Do not run both
simultaneously. Record cold startup and graph/cache warmup separately.

### 9. Calculate measured peak GiB

For each time series:

```bash
python3 - <<'PY'
import csv
p="artifacts/b0-eager-small/gpu-timeseries.csv"
with open(p, encoding="utf-8") as f:
    rows=list(csv.DictReader(f))
peak=max(float(r["memory_used_mib"]) for r in rows)/1024
print(f"peak GiB: {peak:.6f}")
PY
```

Record all three. Sampling may miss shorter peaks; state the interval/limitation.

### 10. Assemble and select measured candidates

```bash
python3 scripts/assemble-measured-results.py \
  --candidate 'b0-eager-small=artifacts/b0-eager-small/results.json=PEAK_GIB' \
  --candidate 'c1-graphs-capacity=artifacts/c1-graphs-capacity/results.json=PEAK_GIB' \
  --candidate 'c2-prefix-cache=artifacts/c2-prefix-cache/results.json=PEAK_GIB' \
  --output artifacts/measured-candidates.json
python3 src/select_candidate.py \
  --slo configs/slo.json \
  --results artifacts/measured-candidates.json \
  --output artifacts/results.json
```

Replace each `PEAK_GIB` with its numeric measurement. If no candidate is
feasible, selector exits 3; that is a valid result.

### 11. Repeatability and ablation

Repeat the winner twice from a declared warm/cold state and repeat the closest
feasible/infeasible alternative. Then ablate one mechanism:

- graph winner: add `--enforce-eager` only;
- prefix winner: disable prefix caching only;
- scheduler winner: restore baseline token/sequence limit only.

Add a new candidate ID rather than overwriting original evidence.

## Inspect what happened

Kubernetes:

```bash
kubectl get deployment,pod,service,endpoints -n oms-lesson-23 -o wide
kubectl get events -n oms-lesson-23 --sort-by=.lastTimestamp
kubectl describe pod -n oms-lesson-23
```

Engine:

```bash
kubectl logs -n oms-lesson-23 deployment/vllm |
  grep -Ei 'model|revision|memory|cache|block|graph|attention|chunk'
curl --fail --silent http://127.0.0.1:8000/metrics \
  > artifacts/current-metrics.txt
```

Evidence chain:

```text
candidate changed configuration
-> startup log confirms mode
-> queue/cache/graph behavior changes
-> per-request distribution changes
-> correctness/quality remains above floor
-> memory/cost remains below cap
```

## Deliberate failure

Break only Service selection:

```bash
./scripts/failure-drill.sh break
kubectl get endpoints vllm -n oms-lesson-23
```

Expected: endpoint addresses become empty. The Pod may remain healthy, proving
that reachability and application health are different layers.

With port-forward running:

```bash
set +e
curl --max-time 5 --fail http://127.0.0.1:8000/health
status=$?
set -e
printf 'expected failure status=%s\n' "$status"
test "$status" -ne 0
```

Repair:

```bash
./scripts/failure-drill.sh repair
until kubectl get endpoints vllm -n oms-lesson-23 \
  -o jsonpath='{.subsets[0].addresses[0].ip}' | grep -q .; do sleep 2; done
curl --fail --silent http://127.0.0.1:8000/health
```

Diagnosis tree:

```text
client cannot reach service
├─ port-forward ended -> local process
├─ Service endpoints empty -> selector/readiness
├─ Pod Pending -> GPU scheduling/resources/taint
├─ Pod CrashLoop -> image/model/args/driver
├─ health fails -> application startup
└─ chat fails only -> model name/request/engine
```

## Controlled experiment

The capstone candidates are bounded treatments. Mechanism explanation comes
from the required ablation. Constants include:

- model ID/revision and image digest;
- one GPU/replica/node type;
- prompt set/hash, sampling, concurrency, request count;
- SLO/quality and success definition;
- endpoint/client version;
- sampling interval and cache-state policy.

Any environment drift forces a new run ID and disclosure.

## Verification

Free gate:

```bash
./scripts/run-cpu-lab.sh
```

Real behavioral gate:

```bash
python3 - <<'PY'
import json, glob
for p in glob.glob("artifacts/*/results.json"):
    d=json.load(open(p, encoding="utf-8"))
    assert d["schema_version"]=="oms-benchmark/v1"
    assert len(d["requests"])==d["workload"]["measured_requests"]
    assert all(r["text_sha256"] for r in d["requests"])
    print(p, d["summary"])
PY
```

Selection gate is `src/select_candidate.py`. Cleanup has a separate proof.

## Expected result

The free fixture selects `c1-graphs-capacity` because the faster `c2` violates
success rate and baseline violates TTFT. Real EKS results are intentionally
unknown. Valid outcomes include:

- one reproducible feasible winner;
- several Pareto-feasible candidates with uncertainty;
- no candidate meeting every gate.

Never copy synthetic figures into the real report.

## Troubleshooting

| Symptom | Layer | Evidence/action |
|---|---|---|
| Pod Pending | scheduling | events, allocatable GPU, taints/selector |
| image pull fails | registry | exact digest, node egress/rate/auth |
| model download fails | artifact/network | revision, license/access, logs |
| startup OOM | memory | candidate config, other processes, logs |
| probe fails | app | `/health`, startup log, timeout |
| port-forward refused | service | endpoints/readiness/local port |
| usage tokens missing | API/version | archived help/response; stop selection |
| TTFT null | streaming/client | SSE events/server behavior |
| quality unexpectedly low | model/workload | hashes, prompts, per-request IDs |
| peak over cap | GPU | time series; reject candidate |
| selector exits 3 | SLO | report infeasible; do not weaken silently |

## Evidence to collect

- `artifacts/contract-sha256.txt`
- image digest, version/help, model revision
- AWS/node-group before state (sanitize before sharing)
- rendered manifest per candidate
- startup logs, events, descriptions, metrics
- raw `oms-benchmark/v1` results
- GPU time series and peak calculation
- measured candidate set and `artifacts/results.json`
- winner repeats, close alternative, ablation
- failure/repair evidence
- `artifacts/report.md`
- node-group/namespace cleanup proof and GPU-minute total

## Knowledge check

1. Why gate before ranking?
2. Why can request throughput be misleading?
3. What does `Recreate` solve on one GPU?
4. Why separate startup/warmup/steady state?
5. Why is 24 requests a weak p95 sample?
6. What makes a candidate treatment different from an ablation?
7. Which evidence connects a graph flag to latency?
8. Why can namespace deletion leave node cost?

## Exercises

Guided:

1. Add a candidate changing only `max_num_seqs`.
2. Make the synthetic fastest candidate pass reliability but exceed memory.
3. Calculate percentile ranks by hand for 24 samples.
4. Add a quality prompt slice and explain its failure mode.

Independent challenge: repeat the capstone with an application-representative
prompt/output distribution and a larger licensed model that fits the fixed
24 GiB budget. Preserve the same evidence contract and justify every change.

See [solutions/SOLUTIONS.md](solutions/SOLUTIONS.md).

## Completion gate

- Free selector/verifier passes and synthetic data is labelled.
- SLO/workload/candidates are frozen and hashed before GPU results.
- Every deployment uses image digest, exact model commit, one GPU, ClusterIP.
- Every candidate has raw request, log/event, metrics, and GPU-series evidence.
- Hard gates reject invalid candidates before ranking.
- Winner is repeated twice and compared with one close alternative.
- One mechanism ablation explains the winner.
- Service failure is diagnosed from empty endpoints and repaired behaviorally.
- Report states uncertainty/limitations and another learner can reproduce it.
- Namespace is gone, GPU node group restored, and total cost/time recorded.

## Cleanup

Stop port-forward with `Ctrl-C`, then:

```bash
./scripts/cleanup.sh
kubectl get namespace oms-lesson-23
kubectl get service --all-namespaces \
  --field-selector metadata.name=vllm
```

Restore the GPU node group to the exact scaling state saved in
`artifacts/nodegroup-before.json` using your reviewed account procedure. Verify:

```bash
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.scalingConfig' \
  --output json |
  tee artifacts/nodegroup-after.json
kubectl get nodes
```

Also check account-approved inventories for load balancers, EBS volumes,
snapshots, and model caches. This lesson creates no LoadBalancer/PVC by default,
so finding one requires investigation. Keep ignored evidence until the report
is complete; sanitize before publishing.

## Primary references

Required, reviewed 2026-10-21:

- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [vLLM v0.28.0 source](https://github.com/vllm-project/vllm/tree/v0.28.0)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/)
- [PagedAttention/vLLM paper](https://arxiv.org/abs/2309.06180)

Optional:

- [AWS EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [NVIDIA DCGM exporter](https://github.com/NVIDIA/dcgm-exporter)

Revalidate image availability, CLI/probe behavior, Kubernetes/EKS versions,
driver compatibility, and current prices on every run.
