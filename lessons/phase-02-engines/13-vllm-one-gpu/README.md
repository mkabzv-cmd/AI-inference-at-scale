# 13 — vLLM on one GPU

**Status:** draft
**Estimated time:** 6–8 hours
**Compute profile:** one NVIDIA GPU Kubernetes node; the small course model fits
comfortably on a 24 GiB A10G-class GPU
**Estimated GPU-minutes:** 75–105 for deployment, metric inspection, two
benchmark configurations, and failure recovery
**Estimated cloud cost:** one GPU node while active, one temporary 20 GiB PVC,
image/model transfer, and existing EKS/network costs; calculate from current
Regional pricing
**Prerequisites:** lessons 11–12; a working EKS GPU node group and device
plugin, approved StorageClass, Docker Buildx for digest inspection, `kubectl`,
Python benchmark environment, and `curl`
**Last validated:** 2026-10-21, static checks only; clean vLLM/GPU/EKS run
pending
**Validated with:** official vLLM 0.28.0 documentation and image tag
`vllm/vllm-openai:v0.28.0`, Qwen model commit
`7ae557604adf67be50417f59c2c2f167def9a775`, Python/Bash/JSON syntax checks,
and manifest rendering; the image digest is intentionally resolved at lab time

## Why this matters

Lesson 11 let one Python `generate` call own the GPU until completion. That
implementation is readable, but concurrent requests line up behind a global
lock. vLLM introduces an engine scheduler and a managed KV-cache pool so
multiple active sequences can share decode iterations.

The important idea is not “vLLM has a faster API.” It is a different execution
model:

```text
independent HTTP requests
        ↓
request validation/tokenization
        ↓
scheduler chooses runnable sequence work
        ↓
model runner executes a batch for this iteration
        ↓
KV blocks retained/reused until sequence completes
        ↓
tokens stream back while arrivals/completions continue
```

You will deploy vLLM's OpenAI-compatible server by immutable image digest,
serve the same model/revision/prompts used by the reference server, inspect
metrics/logs/GPU memory, and change exactly one scheduler capacity control.

## Learning outcomes

By the end, you can:

- deploy vLLM 0.28.0 to one Kubernetes GPU by image digest;
- use an immutable model revision and a stable served model alias;
- explain continuous batching versus a fixed batch and a global request lock;
- explain why paged KV management reduces allocator fragmentation without
  making KV memory free;
- map `gpu-memory-utilization`, `max-model-len`, and `max-num-seqs` to capacity
  and admission trade-offs;
- inspect health, model listing, chat behavior, metrics, logs, Pod placement,
  and GPU telemetry;
- compare vLLM to lesson 11 with the same `oms-benchmark/v1` workload;
- diagnose an invalid engine memory setting from CrashLoopBackOff logs;
- roll back the failed Deployment; and
- delete storage/workload and restore GPU capacity.

## What you will build

```mermaid
flowchart LR
    C[Benchmark client] -->|port-forward| S[ClusterIP Service]
    S --> A[vLLM OpenAI API]
    A --> E[Engine]
    E --> SCH[Scheduler]
    SCH --> MR[Model runner]
    SCH --> KV[KV-cache block pool]
    MR --> GPU[one GPU]
    KV --> GPU
    PVC[(Hub cache PVC)] --> A
    M[/metrics] --> OBS[Evidence]
```

The service exposes `/health`, `/v1/models`, `/v1/chat/completions`, and
`/metrics`. Exact metric names can change across versions, so evidence records
the engine version and stores the raw exposition.

## Files in this lesson

```text
13-vllm-one-gpu/
├── README.md
├── config/engine.json
├── k8s/workload.yaml.tpl
├── requests/smoke.json
└── scripts/
    ├── benchmark.sh
    ├── cleanup.sh
    ├── deploy.sh
    ├── failure-drill.sh
    ├── observe.sh
    ├── preflight.sh
    ├── render.py
    ├── resolve-image.sh
    └── test-api.sh
```

`engine.json` is the human-readable frozen configuration. The Kubernetes
template repeats those values because the deployed manifest is authoritative.
Always compare them during review.

## Concepts and mental model

### Continuous batching

A traditional static batch waits for several inputs, pads them, runs the full
batch, and returns when all are done. LLM requests arrive at different times
and generate different lengths. Waiting for a whole static batch wastes time;
keeping completed sequences in it wastes decode slots.

A continuous scheduler can admit new work and retire finished sequences at
iteration boundaries. Conceptually, an iteration might evolve:

```text
iteration 1: request A prefill
iteration 2: A decode + request B prefill
iteration 3: A decode + B decode + request C prefill
iteration 4: B decode + C decode       (A finished)
```

Real scheduling includes token budgets, memory availability, priorities, and
other policies. “Continuous” does not mean arbitrary mid-kernel changes.

### Paged KV-cache management

Each active sequence needs attention keys/values from earlier tokens. Exact
memory depends on model architecture, dtype, layers, KV heads/head dimension,
and tokens. If every request receives one large contiguous maximum-length
buffer, short/variable requests waste capacity and fragmentation can prevent
useful allocations.

Paged management divides cache space into blocks and maps logical sequence
positions to physical blocks. This resembles virtual-memory paging as an
ownership analogy, but GPU cache blocks are engine-managed tensor storage, not
operating-system pages. Blocks improve placement/reuse and reduce wasted
contiguous reservations; they do not remove the bytes required for live tokens.

### Three controls with different meanings

- `--max-model-len 4096`: maximum context considered by this server
  configuration. Larger values increase potential KV demand.
- `--gpu-memory-utilization 0.80`: fraction of device memory vLLM may target for
  this instance's executor/cache planning. It is not the current utilization
  shown by `nvidia-smi`.
- `--max-num-seqs 16`: cap on sequences processed in a scheduler iteration.
  Raising it can improve concurrency until compute/memory overhead or queueing
  dominates.

No single flag is a universal “performance” knob.

## Under the hood

The container starts the vLLM OpenAI server. During startup it:

1. validates CLI arguments;
2. resolves the exact model commit through the Hub cache;
3. loads tokenizer/config/weights;
4. initializes CUDA execution and memory planning;
5. creates engine/scheduler/model-runner state;
6. becomes healthy only after initialization succeeds.

For a request, the HTTP layer validates the OpenAI-style object and resolves
`course-model` to the loaded model. Tokenized prompt work enters the engine.
The scheduler chooses prefill/decode work subject to token, sequence, and KV
capacity. The model runner executes selected tensor operations. Generated token
IDs return through detokenization/streaming.

The scheduler must handle a two-dimensional resource problem:

```text
compute budget per iteration
+ KV blocks held by all active/request prefixes
```

When cache capacity is tight, the engine may delay admission or use supported
preemption/recomputation behavior. A high request count therefore affects TTFT
through queueing even if per-step decode kernels remain fast.

Do not infer internal behavior solely from latency. Correlate raw metrics,
versioned logs, request distributions, and GPU memory. When a metric's meaning
is unclear, use that exact version's official documentation/source.

## Prerequisites and preflight

From:

```bash
cd lessons/phase-02-engines/13-vllm-one-gpu
chmod +x scripts/*.sh scripts/render.py
```

Set:

```bash
export AWS_REGION=us-east-1
export EKS_CLUSTER=replace-with-lab-cluster
export GPU_NODEGROUP=replace-with-dedicated-nodegroup
export LAB_NAMESPACE=open-models-l13
export MODEL_STORAGE_CLASS=model-cache-gp3
export GPU_NODE_SELECTOR_KEY=eks.amazonaws.com/nodegroup
export GPU_NODE_SELECTOR_VALUE="$GPU_NODEGROUP"
```

Resolve the reviewed tag to the registry's current digest:

```bash
./scripts/resolve-image.sh
cat artifacts/image-digest.txt
./scripts/preflight.sh
```

Digest resolution is a promotion step: review vulnerability/license policy and
record the selected digest. A tag identifies a release conveniently; the digest
identifies deployed bytes.

Inspect node driver/GPU using an existing smoke Pod from lesson 07. The vLLM
image's CUDA runtime must be compatible with the node driver. Do not downgrade
or replace drivers on a shared node to force one image to run.

## Cost and safety

Record node-group scaling before any update:

```bash
mkdir -p artifacts
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.{instanceTypes:instanceTypes,scaling:scalingConfig}' \
  --output json >artifacts/nodegroup-before.json
```

Limits in the manifest:

- one replica;
- exactly one `nvidia.com/gpu`;
- maximum engine utilization setting 0.95 enforced by renderer;
- maximum 64 scheduler sequences enforced by renderer;
- private `ClusterIP`;
- 20 GiB PVC;
- small public model requiring no token.

Stop on unexpected identity/context, shared node group, public Service, mutable
image reference, unexplained model access, repeated GPU Xid/health errors, or
cleanup failure.

## Predict before running

1. Why may vLLM reserve more GPU memory at startup than the lesson 11 server?
2. Does `gpu-memory-utilization=0.8` mean GPU compute stays 80% busy?
3. At concurrency one, should continuous batching provide its largest benefit?
4. Which metric should worsen when requests wait for admission?
5. Can higher `max-num-seqs` reduce performance?
6. Why does a tiny model not prove a larger model will fit with the same flags?
7. What evidence proves the same model revision was used?
8. Why is a digest necessary even with a versioned tag?

## Lab outline

1. Resolve and review the vLLM image digest.
2. render and server-dry-run a one-GPU private Deployment.
3. deploy and verify the API behavior/model identity.
4. inspect logs, metrics, GPU memory, and process placement.
5. replay the shared benchmark at fixed concurrency.
6. compare `max-num-seqs=1` versus `16`.
7. apply an invalid memory fraction, diagnose startup failure, and roll back.
8. collect evidence and remove every chargeable lab resource.

## Step-by-step lab

### 1. Validate files

```bash
python3 -m py_compile scripts/render.py
python3 -m json.tool config/engine.json >/dev/null
python3 -m json.tool requests/smoke.json >/dev/null
bash -n scripts/*.sh
```

### 2. Render baseline

```bash
source artifacts/image.env
export IMAGE_URI
export GPU_MEMORY_UTILIZATION=0.80
export MAX_NUM_SEQS=16
python3 scripts/render.py
grep -E 'image:|gpu-memory|max-num-seqs|nvidia.com/gpu|type:' \
  artifacts/rendered.yaml
kubectl apply --dry-run=server -f artifacts/rendered.yaml
```

Expected: one digest image, one GPU request/limit, ClusterIP, correct model
revision, memory fraction `0.80`, and sequence cap `16`.

### 3. Deploy and wait

```bash
./scripts/deploy.sh
kubectl get pod -n "$LAB_NAMESPACE" -w
```

First startup may download the model. In another terminal:

```bash
kubectl logs -n "$LAB_NAMESPACE" deployment/vllm --follow
```

Read logs as evidence but avoid depending on an exact wording across versions.

### 4. Behavioral verification

```bash
./scripts/test-api.sh
python3 -m json.tool artifacts/smoke-response.json
grep -E 'request|token|cache|queue|running' artifacts/metrics.txt | head -60
```

`test-api.sh` requires the served alias, nonempty generated content, positive
completion-token count, and a metrics response.

### 5. Benchmark the baseline

Keep the script's port-forward or run:

```bash
kubectl port-forward --address 127.0.0.1 \
  -n "$LAB_NAMESPACE" service/vllm 8000:8000
```

From another terminal with lesson 12's venv active:

```bash
export BENCH_BASE_URL=http://127.0.0.1:8000
export CONCURRENCY=4
./scripts/benchmark.sh
```

This writes `artifacts/results-c4.json` using the same tokenizer, prompts,
sampling, and schema as the reference server.

### 6. Inspect

```bash
./scripts/observe.sh
sed -n '1,160p' artifacts/vllm.log
cat artifacts/nvidia-smi.csv
python3 -m json.tool artifacts/results-c4.json | sed -n '1,220p'
```

Record Pod image ID/digest, exact args, vLLM version, model revision, driver/GPU,
metric exposition, and raw requests.

### 7. One-variable scheduler experiment

Save baseline, then change only `max-num-seqs`:

```bash
cp artifacts/results-c4.json artifacts/results-maxseqs16-c4.json
export MAX_NUM_SEQS=1
./scripts/deploy.sh
./scripts/test-api.sh
CONCURRENCY=4 ./scripts/benchmark.sh
mv artifacts/results-c4.json artifacts/results-maxseqs1-c4.json
```

Restore:

```bash
export MAX_NUM_SEQS=16
./scripts/deploy.sh
```

Compare success/quality first, then throughput, TTFT, TPOT, and memory. Because
only four concurrent clients are used, do not extrapolate to very high load.

## Inspect what happened

During a benchmark:

```bash
watch -n 1 kubectl exec -n "$LAB_NAMESPACE" deployment/vllm -- nvidia-smi
curl --silent http://127.0.0.1:8000/metrics >artifacts/metrics-during-load.txt
kubectl top pod -n "$LAB_NAMESPACE"
```

If Metrics Server is absent, `kubectl top` may fail; that does not invalidate
GPU evidence. Use `nvidia-smi`, engine metrics, logs, and client timing.

## Deliberate failure

Run:

```bash
./scripts/failure-drill.sh
```

The script patches the CLI value of `gpu-memory-utilization` from `0.80` to
invalid `1.20`. The replacement Pod should fail argument/config validation,
not become ready. It captures rollout state/logs, requires an error clue, then
uses `kubectl rollout undo`.

Diagnosis:

```text
new Pod unavailable
├─ Pending -> scheduler/GPU/PVC
├─ ImagePullBackOff -> image digest/registry
├─ CrashLoopBackOff + argument error -> engine configuration
└─ Running, Unready -> startup/model/CUDA/health
```

The expected failure is version-dependent in wording. Diagnose by layer and
invalid value, not one exact log sentence.

## Controlled experiment

The only changed engine variable is `max-num-seqs: 16 -> 1`. Everything else
must match:

- image digest and vLLM version;
- model ID/revision;
- model length/dtype/memory fraction;
- prompt hash/sampling/max output;
- hardware and resource limits;
- benchmark concurrency/repetitions.

If another field changed during render/restart, the result is contaminated and
must be rerun.

## Verification

```bash
./scripts/test-api.sh
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  artifacts/results-maxseqs16-c4.json
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  artifacts/results-maxseqs1-c4.json
kubectl get deployment/vllm -n "$LAB_NAMESPACE" \
  -o jsonpath='{.status.readyReplicas}{"\n"}'
```

Expected ready replicas: `1`. Behavioral/quality checks must also pass.

## Expected result

The API returns a standard chat completion with nonempty content and usage.
Metrics contain vLLM-prefixed/request/cache/queue-related series appropriate to
0.28.0. Benchmark JSON has:

```text
schema_version = oms-benchmark/v1
engine.name     = vllm
engine.version  = 0.28.0
model.revision  = 7ae557...
success_rate    = 1.0
```

No numeric performance target is supplied because unmeasured course prose
should not impersonate evidence.

## Troubleshooting

| Symptom | Layer | Evidence/action |
|---|---|---|
| digest resolution fails | registry/network | inspect tag, Docker auth/network |
| Pending | scheduling | Pod events, selector, taint, GPU/PVC |
| CUDA/driver error | runtime | logs, node driver, image CUDA contract |
| model access error | artifact | revision, outbound path, cache permissions |
| engine init OOM | memory config | logs, fraction, model length, GPU processes |
| health never succeeds | application | startup logs and `/health` |
| 404 model | API alias | `/v1/models`, request `model` |
| benchmark no TTFT | streaming | raw SSE/API compatibility |
| low quality | model/template/settings | revision, alias, request fixture |
| metric absent | version/config | raw `/metrics`, exact docs/source |

## Evidence to collect

```text
artifacts/
├── image.env
├── image-digest.txt
├── nodegroup-before.json
├── rendered.yaml
├── models.json
├── smoke-response.json
├── metrics.txt
├── vllm.log
├── nvidia-smi.csv
├── results-maxseqs16-c4.json
├── results-maxseqs1-c4.json
├── failure.log
├── results.json
└── report.md
```

`results.json` should point to raw benchmark files, not copy only “best” values.
`report.md` explains observed differences and uncertainty. Sanitize cloud
identifiers before publication.

## Knowledge check

1. Why can paged KV allocation admit more variable-length requests?
2. Why is allocated KV capacity not the same as GPU compute utilization?
3. How does continuous batching affect queue wait and decode batches?
4. Which flag constrains context capacity versus sequence concurrency?
5. Why can a higher concurrency cap hurt tail latency?
6. What evidence distinguishes engine configuration from scheduling failure?
7. Why must image digest and model revision both be recorded?

## Exercises

Guided: inspect metrics before/during concurrency four and classify each useful
series as arrival, queue, running, cache, token, or latency evidence.

Independent: repeat `max-num-seqs` at concurrency 1, 4, and 16 with three runs
each. Explain where the setting matters and where another bottleneck dominates.

<details>
<summary>Solution guidance</summary>

Validate every JSON, group by concurrency/config, use medians plus raw ranges,
and correlate with cache/queue metrics. A difference smaller than run-to-run
noise is not a useful conclusion.

</details>

## Completion gate

Complete when API/quality checks pass; exact image/model/config are recorded;
you can diagram scheduler/model runner/KV ownership; raw vLLM metrics and GPU
evidence are saved; one-variable results are valid; the invalid fraction is
diagnosed and rolled back; and cleanup/capacity restoration are proved.

## Cleanup

```bash
./scripts/cleanup.sh
! kubectl get namespace "$LAB_NAMESPACE"
```

Restore the saved node-group scaling values using the reviewed AWS command from
lesson 11. Check PVC/PV deletion and any retained Hub/ECR storage:

```bash
kubectl get pv
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.scalingConfig'
```

## Primary references

Official/original sources reviewed 2026-10-21:

- [vLLM installation with NVIDIA CUDA](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)
- [vLLM engine arguments](https://docs.vllm.ai/en/latest/configuration/engine_args/)
- [vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/)
- [vLLM paged attention design](https://docs.vllm.ai/en/latest/design/paged_attention/)
- [vLLM 0.28.0 release](https://github.com/vllm-project/vllm/releases/tag/v0.28.0)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Pinned Qwen model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)
- [PagedAttention paper](https://arxiv.org/abs/2309.06180)
