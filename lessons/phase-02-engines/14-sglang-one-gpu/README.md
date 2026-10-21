# 14 — SGLang on one GPU

**Status:** draft
**Estimated time:** 7–9 hours
**Compute profile:** one NVIDIA GPU node with a driver compatible with the
pinned CUDA 13 image; a 24 GiB A10G-class GPU is sufficient for the course model
**Estimated GPU-minutes:** 90–120 for deployment, structured-output checks,
prefix-cache experiment, shared benchmark, and rollback drill
**Estimated cloud cost:** one GPU node while active, temporary 20 GiB PVC,
model/image transfer, and existing EKS/network cost; retrieve current Regional
prices before starting
**Prerequisites:** lessons 11–13; lesson 12 benchmark venv, working EKS GPU
node/device plugin, approved StorageClass, Docker Buildx, `kubectl`, and `curl`
**Last validated:** 2026-10-21, static checks only; clean SGLang/GPU/EKS run
pending
**Validated with:** official SGLang v0.5.21 installation/server documentation,
image tag `lmsysorg/sglang:v0.5.21-cu130`, immutable Qwen model revision
`7ae557604adf67be50417f59c2c2f167def9a775`, Python/Bash/JSON validation, and
manifest rendering; registry digest and hardware compatibility are verified by
the learner

## Why this matters

Two engines can expose nearly the same HTTP API but make different choices
about scheduling, reusable prefixes, memory reservation, constrained
generation, kernels, and supported models. Comparing SGLang with vLLM prevents
you from treating one implementation as the definition of “an inference
engine.”

SGLang is especially useful for studying:

- RadixAttention, which represents reusable prompt prefixes so later requests
  can reference matching cached KV state;
- cache-aware scheduling, which can prefer work with useful prefix reuse;
- an OpenAI-compatible server for ordinary clients; and
- structured output, where token choices are constrained to remain compatible
  with a grammar/schema.

You will use the same source model, revision, prompts, sampling, hardware class,
API alias, and benchmark schema as lessons 11 and 13. You will explicitly
record unsupported or version-specific behavior instead of hiding it.

## Learning outcomes

By the end, you can:

- deploy SGLang v0.5.21 by resolved image digest on one GPU;
- explain how a radix tree can represent shared token prefixes;
- distinguish ordinary KV ownership from cross-request prefix reuse;
- explain why a cache hit can reduce prefill work but not decode work for new
  output tokens;
- map `mem-fraction-static`, `context-length`, and
  `max-running-requests` to memory/admission trade-offs;
- request JSON constrained by a schema and verify the returned text parses;
- run a repeated-prefix treatment with RadixAttention enabled/disabled;
- compare SGLang with vLLM/reference results using raw evidence;
- diagnose an invalid static-memory fraction and roll back; and
- verify namespace, PVC, and GPU capacity cleanup.

## What you will build

```mermaid
flowchart LR
    C[Client] -->|OpenAI chat request| API[SGLang server]
    API --> TOK[Tokenizer]
    TOK --> SCH[Scheduler]
    SCH --> R[Radix prefix cache]
    SCH --> RUN[Model runner]
    R --> KV[KV blocks]
    RUN --> GPU[one GPU]
    API --> CG[Constrained generation]
    CG --> J[JSON-schema-valid text]
    M[/metrics and logs] --> E[Evidence]
```

The lab proves ordinary chat, model listing, structured JSON, repeated-prefix
requests, metrics/logs, and the shared benchmark contract. Service type remains
`ClusterIP`.

## Files in this lesson

```text
14-sglang-one-gpu/
├── README.md
├── config/engine.json
├── k8s/workload.yaml.tpl
├── requests/
│   ├── smoke.json
│   ├── structured.json
│   ├── repeated-prefix-a.json
│   └── repeated-prefix-b.json
└── scripts/
    ├── benchmark.sh
    ├── cleanup.sh
    ├── deploy.sh
    ├── failure-drill.sh
    ├── observe.sh
    ├── prefix-experiment.py
    ├── preflight.sh
    ├── render.py
    ├── resolve-image.sh
    └── test-api.sh
```

The two prefix fixtures share an identical system message and differ only in
the final user question. `structured.json` uses the OpenAI `response_format`
JSON-schema shape supported by the pinned server path.

## Concepts and mental model

### Prefix reuse starts with token identity

Suppose requests begin with token sequences:

```text
A = [10, 20, 30, 40, 50]
B = [10, 20, 30, 77, 88]
C = [10, 20, 99]
```

All share `[10, 20]`; A and B additionally share token `30`. A radix tree
compresses common paths:

```text
[10,20]
├── [30]
│   ├── [40,50]  A
│   └── [77,88]  B
└── [99]         C
```

Cached KV data corresponds to model computation for tokens along reusable
paths. A later matching request may skip some repeated prefill. This analogy
does not mean the tree itself contains all model tensors; it is an indexing and
ownership structure associated with KV blocks.

Reuse requires identical token prefixes—not merely sentences that “mean the
same thing.” Chat-template changes, whitespace, tool definitions, ordering, or
different model/tokenizer revisions can destroy a match.

### Cache-aware scheduling is not simply “longest prefix first”

The engine balances cached work, waiting time, memory pressure, and runnable
tokens according to its implemented policy. A cache-aware scheduler may improve
effective compute use, but aggressive preference could affect fairness. Use
metrics and versioned implementation docs; do not invent a policy from one
latency sample.

### Structured output changes token selection

JSON schema does not ask the model politely to emit JSON. The engine compiles
or interprets a constraint and masks token choices that would make the partial
output invalid. Each decode step combines model logits with grammar state.
This provides syntactic structure, not factual truth. A valid object can contain
bad classification text and still needs semantic evaluation.

### Static memory fraction

`--mem-fraction-static 0.75` tells SGLang how much device memory to reserve/use
for model/KV/static engine needs according to this release's semantics. It is
not GPU compute utilization. A value too high can collide with runtime
overhead; too low can constrain cache/concurrency.

## Under the hood

Startup runs `python3 -m sglang.launch_server` with explicit arguments. The
server validates configuration, downloads the exact Hub revision into the PVC,
loads weights/tokenizer, initializes CUDA and cache structures, then serves
health/API traffic.

For a repeated prefix:

1. chat messages are serialized by the model's template and tokenized;
2. the token prefix is looked up in the radix representation;
3. reusable cached states remain referenced while new suffix tokens require
   prefill;
4. the scheduler admits prompt/decode work subject to memory and running-request
   limits;
5. new generated tokens extend sequence state until finish;
6. cache entries may persist/evict according to engine policy and pressure.

For structured generation, grammar state travels alongside sequence state.
After each output token, valid next-token choices are updated. Constraint work
can add overhead, so compare structured and ordinary requests only when that is
the controlled variable.

The manifest explicitly sets:

```text
context length:       4096
static memory fraction: 0.75
max running requests: 16
Radix cache:          enabled by default baseline
```

The renderer can add `--disable-radix-cache` for the controlled experiment. It
enforces conservative value ranges before Kubernetes sees a manifest.

## Prerequisites and preflight

From:

```bash
cd lessons/phase-02-engines/14-sglang-one-gpu
chmod +x scripts/*.sh scripts/*.py
```

Set:

```bash
export AWS_REGION=us-east-1
export EKS_CLUSTER=replace-with-lab-cluster
export GPU_NODEGROUP=replace-with-dedicated-nodegroup
export LAB_NAMESPACE=open-models-l14
export MODEL_STORAGE_CLASS=model-cache-gp3
export GPU_NODE_SELECTOR_KEY=eks.amazonaws.com/nodegroup
export GPU_NODE_SELECTOR_VALUE="$GPU_NODEGROUP"
```

Resolve/review image:

```bash
./scripts/resolve-image.sh
cat artifacts/image-digest.txt
./scripts/preflight.sh
```

The pinned image is a CUDA 13 build. Confirm the EKS node driver supports the
image's CUDA runtime using NVIDIA's compatibility guidance and a smoke test.
If it does not, select a documented compatible SGLang image and record that as
a course refresh; do not silently change the pin or modify a shared host.

## Cost and safety

Record initial node group:

```bash
mkdir -p artifacts
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.{instanceTypes:instanceTypes,scaling:scalingConfig}' \
  --output json >artifacts/nodegroup-before.json
```

Safety limits:

- one replica/one GPU;
- `mem-fraction-static` renderer range `0.10..0.90`;
- maximum 64 running requests in this lesson;
- `ClusterIP` only;
- public pinned model, no committed token;
- 20 GiB PVC;
- one engine deployed at a time for fair comparisons.

Stop on wrong account/context, incompatible driver, shared node, public
exposure, OOM/health error, suspicious model license/access state, or unknown
chargeable resource.

## Predict before running

1. Which request should benefit more from a shared system prefix: the first or
   a later one?
2. Does a prefix hit eliminate generation of new output tokens?
3. What change to whitespace could destroy token-prefix identity?
4. Why can a schema-valid answer still be wrong?
5. How can cache preference affect fairness?
6. What happens when static memory fraction is too high?
7. Which evidence proves Radix cache rather than a warm CUDA kernel caused a
   difference?
8. Why must server image and model revision match across repeats?

## Lab outline

1. Resolve image digest and render a private one-GPU Deployment.
2. deploy/verify chat, model listing, and schema-constrained JSON.
3. inspect startup, cache/scheduler metrics, logs, and GPU memory.
4. run the common `oms-benchmark/v1` workload.
5. run identical repeated-prefix traffic with cache enabled and disabled.
6. introduce invalid static-memory configuration, diagnose, and roll back.
7. document compatibility boundaries and clean up.

## Step-by-step lab

### 1. Static validation

```bash
python3 -m py_compile scripts/*.py
for file in config/*.json requests/*.json; do
  python3 -m json.tool "$file" >/dev/null
done
bash -n scripts/*.sh
```

### 2. Render and review

```bash
source artifacts/image.env
export IMAGE_URI
export MEM_FRACTION_STATIC=0.75
export MAX_RUNNING_REQUESTS=16
export DISABLE_RADIX_CACHE=false
python3 scripts/render.py
grep -E 'image:|model-path|revision|mem-fraction|max-running|radix|type:|nvidia.com/gpu' \
  artifacts/rendered.yaml
kubectl apply --dry-run=server -f artifacts/rendered.yaml
```

Confirm the absence of `--disable-radix-cache` in the baseline.

### 3. Deploy and verify

```bash
./scripts/deploy.sh
kubectl logs -n "$LAB_NAMESPACE" deployment/sglang --follow
```

After rollout:

```bash
./scripts/test-api.sh
python3 -m json.tool artifacts/smoke-response.json
python3 -m json.tool artifacts/structured-response.json
```

The test parses the assistant's structured content as JSON, requires exactly
`category` and `next_action`, and requires nonempty string values. This proves
syntax/shape, not semantic correctness.

### 4. Benchmark common workload

Start:

```bash
kubectl port-forward --address 127.0.0.1 \
  -n "$LAB_NAMESPACE" service/sglang 8000:8000
```

In another terminal with lesson 12 venv:

```bash
export BENCH_BASE_URL=http://127.0.0.1:8000
export CONCURRENCY=4
export RADIX_CACHE_ENABLED=true
./scripts/benchmark.sh
mv artifacts/results-c4.json artifacts/results-radix-on-c4.json
```

### 5. Repeated-prefix observation

With port-forward active:

```bash
python3 scripts/prefix-experiment.py \
  --requests 12 \
  --output artifacts/prefix-radix-on.json
./scripts/observe.sh
```

Latency alone cannot prove cache reuse. Save relevant cache metrics/logs before
and after. Exact series names depend on v0.5.21; store raw output and cite the
version.

### 6. Disable only Radix cache

```bash
export DISABLE_RADIX_CACHE=true
./scripts/deploy.sh
./scripts/test-api.sh
python3 scripts/prefix-experiment.py \
  --requests 12 \
  --output artifacts/prefix-radix-off.json
export RADIX_CACHE_ENABLED=false
./scripts/benchmark.sh
mv artifacts/results-c4.json artifacts/results-radix-off-c4.json
```

Restore:

```bash
export DISABLE_RADIX_CACHE=false
./scripts/deploy.sh
```

Restart before each treatment and run at least three treatment pairs to reduce
order/warmup bias.

## Inspect what happened

```bash
kubectl get pod -n "$LAB_NAMESPACE" -o wide
kubectl get deployment/sglang -n "$LAB_NAMESPACE" -o yaml \
  >artifacts/deployment-current.yaml
kubectl logs -n "$LAB_NAMESPACE" deployment/sglang >artifacts/sglang-current.log
curl --silent http://127.0.0.1:8000/metrics \
  >artifacts/metrics-current.txt
grep -Ei 'cache|prefix|radix|queue|token|running' \
  artifacts/metrics-current.txt | head -80
```

If cache-specific metrics are unavailable, say so. Do not turn a latency
improvement into a proven cache hit without server-side evidence.

## Deliberate failure

```bash
./scripts/failure-drill.sh
```

The script patches `mem-fraction-static` to invalid `1.20`, waits for rollout
failure, captures Pods/logs, searches for a configuration/memory clue, then
rolls back.

```text
replacement unavailable
├─ Pending -> Kubernetes placement/storage
├─ pull failure -> registry/digest
├─ argument/assertion/memory error -> SGLang configuration
└─ CUDA error -> image/driver/device contract
```

Do not “repair” by raising Pod memory; static fraction concerns GPU planning,
not Kubernetes host RAM.

## Controlled experiment

Controlled variable: Radix cache enabled versus `--disable-radix-cache`.
Controlled constants: image digest, model/revision, context length, static
fraction, running-request limit, request sequence, prompt bytes, sampling,
hardware, resource limits, and restart procedure.

Compare:

- first request TTFT;
- later repeated-prefix TTFT;
- request/output throughput;
- quality/success;
- cache metrics and memory;
- run-to-run range.

Avoid comparing enabled-after-warmup against disabled-cold.

## Verification

```bash
./scripts/test-api.sh
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  artifacts/results-radix-on-c4.json
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  artifacts/results-radix-off-c4.json
python3 - <<'PY'
import json
for name in ("prefix-radix-on.json", "prefix-radix-off.json"):
    d=json.load(open("artifacts/"+name))
    assert all(r["nonempty"] for r in d["requests"])
print("prefix treatments are behaviorally valid")
PY
```

## Expected result

Expect valid ordinary chat and schema-shaped JSON, one Ready Pod, exact image
digest/model revision, and `oms-benchmark/v1` records. Repeated matching
prefixes may show reduced prefill-related time when reusable KV is available,
but this lesson supplies no fabricated speedup target. Hardware, prefix length,
memory pressure, and version determine materiality.

## Troubleshooting

| Symptom | Layer | Evidence/action |
|---|---|---|
| CUDA image fails | driver/runtime | image CUDA version, node driver, logs |
| Pod Pending | Kubernetes | events, selector/taint/GPU/PVC |
| model load fails | artifact | exact revision, outbound access/cache |
| health never ready | engine | startup logs, memory fraction/context |
| structured request 400 | API compatibility | error body, exact v0.5.21 docs |
| valid JSON, wrong meaning | model quality | semantic rubric, not parser |
| no prefix benefit | workload/cache | token identity, prefix length, metrics |
| cache evidence absent | observability | raw metrics/source; report limitation |
| low quality | model/template | revision, alias, chat request |

## Evidence to collect

```text
artifacts/
├── image-digest.txt
├── nodegroup-before.json
├── rendered.yaml
├── smoke-response.json
├── structured-response.json
├── prefix-radix-on.json
├── prefix-radix-off.json
├── results-radix-on-c4.json
├── results-radix-off-c4.json
├── metrics-current.txt
├── sglang.log
├── nvidia-smi.csv
├── failure.log
├── results.json
└── report.md
```

Report compatibility gaps explicitly: fields ignored/rejected, schema features,
model families, or metrics missing. Sanitization rules from lesson 12 apply.

## Knowledge check

1. Why must prefixes match as tokens rather than meaning?
2. Which work can a prefix hit skip, and which remains?
3. How does a radix tree represent three partially shared prompts?
4. Why can cache-aware scheduling introduce fairness concerns?
5. What guarantee does constrained JSON provide—and not provide?
6. Why isn't `mem-fraction-static` a compute-utilization target?
7. What evidence is required to claim cache reuse?

## Exercises

Guided: change one character in the shared system message and compare server
cache evidence/TTFT. Explain token-prefix invalidation.

Independent: extend the JSON schema with a three-value enum for `category`.
Verify 20 responses parse and satisfy the enum, then measure structured versus
unstructured TPOT with all other settings fixed.

<details>
<summary>Solution guidance</summary>

Add `"enum": ["capacity", "configuration", "application"]` under category.
Parse assistant content, validate membership locally, retain invalid responses,
and report semantic accuracy separately from syntax.

</details>

## Completion gate

Complete when digest/model/config are recorded; ordinary and structured checks
pass; you can explain radix prefix/KV ownership; cache-on/off treatments retain
raw evidence; common benchmark validates; invalid memory fraction is diagnosed
and rolled back; compatibility notes are honest; and cleanup is proved.

## Cleanup

```bash
./scripts/cleanup.sh
! kubectl get namespace "$LAB_NAMESPACE"
kubectl get pv
```

Restore the GPU node-group values from `artifacts/nodegroup-before.json` and
verify desired/minimum capacity. Retain or delete model/image cache only after
documenting its storage cost and reuse plan.

## Primary references

Official/original sources reviewed 2026-10-21:

- [SGLang installation](https://docs.sglang.ai/get_started/install.html)
- [SGLang server arguments](https://docs.sglang.ai/advanced_features/server_arguments.html)
- [SGLang OpenAI APIs](https://docs.sglang.ai/basic_usage/openai_api_completions.html)
- [SGLang structured outputs](https://docs.sglang.ai/advanced_features/structured_outputs.html)
- [SGLang production metrics](https://docs.sglang.ai/references/production_metrics.html)
- [SGLang RadixAttention paper](https://arxiv.org/abs/2312.07104)
- [SGLang v0.5.21 source tag](https://github.com/sgl-project/sglang/tree/v0.5.21)
- [Pinned Qwen model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)
