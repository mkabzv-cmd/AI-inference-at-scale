# 49 — Final capstone: an open-model platform

**Status:** draft
**Time:** multi-week project; 24–50 focused hours after prerequisites
**Compute:** `local-cpu` for the required verifier; optional bounded `g1` or three separate one-GPU nodes
**GPU budget:** declare a hard currency, GPU-hour, replica, and wall-clock limit before any live run
**Prerequisites:** 00–48
**Last reviewed:** 2026-10-21

## Why this matters

A model that answers one prompt is a demo. A platform is a reproducible,
observable, access-controlled lifecycle that another operator can deploy,
validate, recover, roll back, and remove.

This distinction is easy to miss because open-model work crosses many systems.
The model revision can be correct while the tokenizer is wrong. A LoRA adapter
can load over an incompatible base. Retrieval can use a stale index. A healthy
Pod can serve the wrong release. A fast configuration can fail the frozen
quality set. An autoscaler can request Pods that never receive GPU nodes. A
private Service can still accept every caller inside the network. A rollback
can restore the image while leaving a newer incompatible index. A successful
Kubernetes deletion can leave a node group, volume, load balancer, object
version, or telemetry retention policy producing cost.

The final capstone joins the course into one evidence graph:

```text
source + pinned base model/tokenizer
  + chosen engine and optimization configuration
  + frozen data and evaluation
  + optional adapter
  + optional corpus/index
  + private Kubernetes desired state
  + observed quality/performance/security/reliability/cost evidence
  + immutable promotion and known-good rollback
  + verified teardown inventory
                      |
                      v
             one release contract
```

The required local path is intentionally hardware-free. It validates a
checked-in synthetic workspace, then virtually corrupts model identity, quality
evidence, public exposure, cleanup evidence, and live-run attestation. This
proves that the verifier fails closed. It does **not** claim that a GPU, model,
cluster, authentication gateway, benchmark, or teardown ran.

Your capstone path uses `validation_mode: operator-run`. It reuses the actual
artifacts and scripts from earlier lessons, collects observed evidence, binds
every file by SHA-256, and invokes the verifier with
`--require-operator-run`. A passing synthetic fixture can never satisfy that
completion command.

You may choose either:

- a one-GPU service, recommended for the first complete platform; or
- a three-node service with one GPU per ordinary G-family node, intended to
  teach rank orchestration, tensor/pipeline partitioning, network cost, and
  worker-failure behavior.

The three-node path is allowed to be slower. Its value is systems learning, not
winning a benchmark. It does not assume cross-node NVLink. Record the network
you actually have, measure collectives and end-to-end behavior, and state the
boundary of every result.

## Learning outcomes

By the end, you can:

- translate a user workload into a quality target, SLO, security boundary, and
  cost envelope;
- select a one-GPU or three-node topology from model fit and learning goals;
- pin a base model and tokenizer to immutable revisions;
- select an inference engine from measured workload evidence rather than
  popularity;
- explain how prefill, decode, batching, KV cache, quantization, kernels,
  compilation, prefix reuse, and speculative decoding affect the chosen path;
- preserve one exact serving configuration and hash it into the release;
- freeze evaluation inputs before tuning or adaptation;
- attach an optional LoRA/QLoRA adapter to its exact base revision;
- attach an optional RAG corpus/index to versioned source, chunking, embedding,
  authorization, and evaluation evidence;
- package image, model, adapter, index, configuration, and gates as one
  immutable compatibility contract;
- render a digest-pinned, private `ClusterIP` Kubernetes workload with
  restricted Pod controls and default-deny networking;
- distinguish desired state, runtime identity, and observed behavior;
- propagate request/trace identity and correlate client, engine, GPU, Pod, and
  node evidence;
- derive capacity and autoscaling policy from queue, TTFT, token throughput,
  readiness, and measured cold start;
- verify anonymous denial, authenticated-but-unauthorized denial, and one
  authorized action before attaching restricted content;
- threat-model artifacts, identities, tenant boundaries, prompts, retrieval,
  telemetry, CI, GitOps, and deletion;
- run a bounded failure drill and measure degradation and recovery;
- promote one immutable candidate and roll back to a known-good release;
- distinguish estimated cost from observed or billed evidence;
- prove load stopped, endpoints disappeared, GPU capacity was released, and no
  unintended billable resource remains;
- hand a second operator a repository and evidence workspace that can be
  independently reproduced and rejected if inconsistent.

## What you will build

The deliverable has two parts.

First, the repository path in this lesson provides:

- a JSON Schema and prose capstone contract;
- architecture, data-flow, and promotion/teardown diagrams;
- no-overwrite workspace initialization;
- environment, release, serving, evaluation, adapter, RAG, quality,
  performance, security, reliability, cost, cleanup, ADR, threat-model, and
  runbook templates;
- a private digest-pinned Kubernetes composition;
- a typed-confirmation wrapper for invoking an earlier lesson script;
- a finalizer that binds artifact and evidence hashes;
- a standard-library verifier that checks IDs, hashes, exact inventory,
  topology arithmetic, evidence origin, thresholds, access controls,
  promotion, rollback, and cleanup;
- one synthetic passing fixture and five failing overlays;
- a fully runnable CPU fixture suite.

Second, you create an ignored operator workspace containing exactly:

```text
contract.json
environment.json
release.json
evidence-index.json
ADR.md
COST-PLAN.md
RUNBOOK.md
THREAT-MODEL.md
artifact-records/
  adapter.json
  eval-dataset.json
  rag-index.json
  serving-config.json
evidence/
  quality.json
  performance.json
  security.json
  reliability.json
  cost.json
  cleanup.json
k8s/
  platform.yaml
```

Large private weights, datasets, raw prompts, raw responses, indexes, and
telemetry do not belong in Git. Store them in an approved immutable location.
The small manifests above record revisions, hashes, locations that are safe to
share, and the evidence boundary.

The release has six mandatory gates:

| Gate | Minimum proof |
|---|---|
| Quality | Frozen dataset hash, predeclared threshold, baseline/candidate result, all critical safety cases |
| Performance | Frozen workload, sample count, TTFT/latency/error limits, token throughput, raw-results hash |
| Security | Anonymous and unauthorized denial, authorized request, no public exposure, workload policy, provenance, tenant negatives |
| Reliability | Bounded failure, recovery, known-good rollback, post-rollback smoke, second-operator reproduction |
| Cost | Currency budget, GPU-hour budget, estimate inputs, observed amount, billing/measurement source |
| Cleanup | Before/actions/after inventory, stopped load, removed endpoint, released GPU capacity, zero residual billable resources |

## Files in this lesson

```text
49-final-capstone-open-model-platform/
├── README.md
├── CAPSTONE-CONTRACT.md
├── capstone.schema.json
├── docs/
│   ├── architecture.md
│   ├── data-flow.md
│   └── release-sequence.md
├── fixtures/
│   ├── failures/
│   │   ├── fabricated-live-claim.json
│   │   ├── mismatched-model-revision.json
│   │   ├── missing-quality-evidence.json
│   │   ├── public-exposure.json
│   │   └── unverified-cleanup.json
│   └── passing/
│       ├── artifact-records/
│       ├── evidence/
│       ├── k8s/
│       ├── contract.json
│       ├── environment.json
│       ├── evidence-index.json
│       └── release.json
├── scripts/
│   ├── finalize-workspace.sh
│   ├── init-workspace.sh
│   ├── render-private-manifest.sh
│   ├── run-deliberate-failure.sh
│   ├── run-local-lab.sh
│   ├── run-step.sh
│   └── verify.sh
├── solutions/
│   └── SOLUTIONS.md
├── src/
│   ├── finalize_workspace.py
│   ├── init_workspace.py
│   ├── render_private_manifest.py
│   ├── run_explicit_step.py
│   └── verify_capstone.py
└── templates/
    ├── artifact-records/
    ├── evidence/
    ├── k8s/
    ├── ADR.md
    ├── COST-PLAN.md
    ├── RUNBOOK.md
    ├── THREAT-MODEL.md
    ├── contract.json
    ├── environment.json
    └── release.json
```

## Under the hood

### A release is a compatibility graph

`release.json` is not a list of interesting metadata. Every field forms an edge
that must remain true at runtime:

```text
model revision == tokenizer revision
adapter base revision == model revision
serving configuration hash == deployed configuration bytes
evaluation dataset hash == dataset used for quality evidence
RAG corpus/index version == runtime retrieval version
manifest image digest == release image digest
gate evidence hash == exact observed evidence bytes
runtime release ID == promoted release ID
rollback target == previously verified known-good release
```

The verifier loads the contract, release, environment, artifacts, evidence, and
Kubernetes manifest. It checks each relationship and recomputes SHA-256 over
the actual files. `evidence-index.json` must list exactly the files in
`contract.required_files`; extra and missing files fail. Symlinks fail so a
workspace cannot silently point outside its reviewed root.

Hashes prove byte identity relative to a trusted expected hash. They do not
prove who authored bytes, whether a license permits use, whether a build was
isolated, whether an evaluation is representative, or whether an operator was
truthful. Signed provenance, protected CI, independent review, admission
policy, and live negative tests add different claims.

### Evidence origin and the honesty boundary

Every gate includes:

```json
{
  "origin": "observed",
  "claim_scope": "private staging, declared workload and hardware only",
  "attestation": {
    "actor": "named operator or workload identity",
    "observed_at": "ISO-8601 time",
    "command": "exact command or pipeline job",
    "result_source": "immutable raw result location and hash",
    "live_environment": true
  }
}
```

An operator-run requires `origin: observed` and `live_environment: true`. The
checked fixture requires `origin: synthetic` and
`claim_scope: verifier-exercise-only`. The verifier reports
`live_release_qualified=false` for that fixture even when every structural rule
passes.

No static checker can detect every fabricated human claim. This verifier
reduces ambiguity: it rejects an origin/mode mismatch, requires commands and
raw-result hashes, recomputes all local bindings, and requires another operator
to reproduce. Your organization should additionally protect evidence storage,
sign attestations, restrict promotion rights, and audit changes.

### One GPU versus three ordinary GPU nodes

Start with the smallest system that answers the learning question.

For `one-gpu`, the capstone requires:

```text
tensor parallel = 1
pipeline parallel = 1
data parallel = 1
nodes = 1
GPUs per node = 1
```

Choose a model/precision that fits weights, runtime allocations, KV cache, and
headroom. This path is best for learning the full lifecycle without distributed
failures masking basic mistakes.

For `three-node`, the course assumes one GPU per node. To split one model, the
verifier requires `TP × PP = 3` and `DP = 1`; data parallelism does not make an oversized
model fit because each replica still needs a model-parallel copy. Record
rendezvous, rank mapping, placement, actual network interface, NCCL settings,
collective measurements, and a worker-loss timeline.

Ordinary cross-node networking will often make fine-grained tensor parallelism
communication-heavy. Pipeline parallelism may communicate fewer, larger
activation transfers but creates bubbles and stage imbalance. The point is to
measure and explain. Do not describe cross-node NVLink when nodes communicate
over ordinary network interfaces.

### Engine and optimization decisions

Reuse lessons 11–16 to establish a baseline and engine comparison. The capstone
serving manifest records engine name/version and a single JSON configuration.
That configuration includes parallel sizes, dtype/quantization, maximum context
and concurrency, GPU-memory target, request bounds, prefix cache, chunked
prefill, and speculative decoding.

Use lessons 17–23 to change one mechanism at a time. A final configuration is
accepted only after:

1. memory accounting predicts fit with headroom;
2. the frozen workload produces comparable raw requests;
3. the frozen quality set still passes;
4. warmup and measurement windows are separated;
5. queue, TTFT, ITL, total latency, errors, and token throughput are recorded;
6. the image/model/config/hardware boundary is retained.

An optimization is not inherited truth. Quantization can change quality and
kernel availability. Prefix caching depends on exact prefix reuse. Speculative
decoding depends on draft acceptance and added work. CUDA graphs trade dynamic
flexibility for replay efficiency. Re-test the release you actually deploy.

### Optional adaptation

The capstone does not require fine-tuning merely because the course teaches it.
Use the decision from lessons 32–39:

- prefer prompt/system design for instructions that do not require changing
  weights;
- prefer RAG for frequently changing or source-grounded knowledge;
- use LoRA/QLoRA when behavior, style, format, or domain adaptation clears a
  frozen evaluation and justifies lifecycle complexity;
- use distributed training only when model/state fit or the study itself
  requires it.

If adapter support is enabled, `artifact-records/adapter.json` records format, exact
base revision, adapter-byte hash, training dataset revision, training code
revision, and license review. The release hashes that manifest and repeats the
base binding. Run evaluation against base and adapted variants; do not promote
an adapter based only on decreasing training loss.

### Optional RAG

If RAG is enabled, `artifact-records/rag-index.json` records immutable corpus/index
versions, embedding-model revision, chunker-configuration hash, index hash,
authorization-filter stage, and license review. Reuse lessons 40–44 for
ingestion determinism, retrieval evaluation, grounded generation, citation
validation, abstention, prompt-injection handling, and corpus rollback.

Tenant authorization must be applied before unauthorized text enters the model
prompt. A model instruction cannot repair cross-tenant retrieval. Treat
retrieved documents as untrusted content and preserve source/index identity in
responses and traces.

### Private deployment and access release gate

The renderer produces a Namespace, ServiceAccount, Deployment, `ClusterIP`
Service, default-deny NetworkPolicy, and an explicit path from an authenticated
gateway. It includes restricted Pod-security labels, non-root execution,
runtime-default seccomp, no privilege escalation, dropped capabilities,
read-only root filesystem, bounded writable temporary storage, disabled API
token mounting, probes, resources, and a digest-pinned image.

These controls are necessary but not sufficient. `ClusterIP` and NetworkPolicy
do not authenticate a caller. Before attaching restricted model/data content:

1. deploy an empty or nonrestricted private origin;
2. attach the supported identity gateway and action/tenant authorization;
3. require an identifiable anonymous 401/403 from that gate;
4. require denial for an authenticated but unauthorized principal;
5. require one authorized action for the correct tenant;
6. attach restricted content;
7. repeat all three tests after promotion and rollback.

The security evidence records those outcomes. A timeout, DNS error, or denial
from an unrelated layer is not proof.

### Observability, capacity, and autoscaling

Reuse lesson 45’s measurement chain:

```text
request/trace ID
 -> gateway/retrieval
 -> engine queue
 -> prefill and TTFT
 -> decode and ITL
 -> completion/error
 -> engine, GPU, Pod, and node state
```

Retain raw request records and low-cardinality aggregate metrics. Capacity is
valid only for the declared model, engine, configuration, hardware, prompt and
output distributions, concurrency/arrival process, cache state, and quality
gate.

Reuse lesson 46 to distinguish Pod desire from ready GPU capacity. A new
replica may wait for scheduling, node provisioning, GPU registration, image
pull, model load, compilation, warmup, and readiness. Scale from the first
measured saturation signal—often queue or token backlog—not generic CPU by
habit. Bound queues, replicas, scale rates, and scale-down delay. Record metric
loss behavior and cost stop conditions.

### Promotion, rollback, and reproduction

Reuse lesson 48’s sequence: validate, render, stage, prove runtime identity,
smoke/evaluate/load/security test, then promote the same immutable release.
Build once. Rebuilding for production creates another release.

The release names a known-good rollback target before failure injection. A
valid reliability gate includes the failure, bounded degradation, readiness
recovery, pointer rollback, reconciliation, post-rollback behavioral check, and
access-denial recheck.

Finally, a second operator starts from a clean checkout and follows the
runbook. They must be able to reproduce or identify a precise missing
dependency. “It works on the author’s shell” is not a completion criterion.

### Cleanup as a release gate

Cleanup is intentionally mandatory and occurs before the final evidence bind.
`evidence/cleanup.json` contains a scoped before-inventory, exact teardown
actions, empty after-inventory, empty residual-billable list, stopped load
generators, removed endpoint, released GPU capacity, and verification commands.

Cloud deletion is asynchronous. Wait and re-inventory node groups/provisioners,
instances, volumes/snapshots, load balancers/target groups, addresses,
filesystems, object versions, registry artifacts, log groups/retention, queues,
databases, and any experiment-created IAM or network object. List intentionally
retained artifacts and ongoing cost in `COST-PLAN.md`.

## Prerequisites and preflight

Run from this lesson:

```bash
cd lessons/phase-07-production/49-final-capstone-open-model-platform
python3 --version
git status --short
python3 -m json.tool capstone.schema.json >/dev/null
find scripts -type f -name '*.sh' -exec bash -n {} +
```

Run the CPU contract suite before spending anything:

```bash
chmod +x scripts/*.sh src/*.py
./scripts/run-local-lab.sh
```

Expected ending:

```text
PASS: completion mode rejects synthetic evidence
PASS: initializer is no-overwrite and starter evidence fails closed
PASS: lesson-49 local fixture suite completed
```

For a live capstone, preflight every selected component:

- `kubectl config current-context` is the intended cluster;
- namespace and region are explicitly recorded;
- GPU capacity/quota and scheduling labels are understood;
- registry, model, adapter, index, and telemetry access use workload identity;
- image and model revisions are immutable;
- Service and gateway are private;
- anonymous/unauthorized tests have an owner;
- workload and evaluation inputs are frozen;
- known-good rollback release exists;
- budget and wall-clock alarms exist;
- teardown owner and inventory commands are written before deployment.

Do not begin if you cannot identify the account/project, region, cluster,
namespace, active node provisioning mechanism, and person authorized to stop
the run.

## Cost and safety

The required fixture suite uses CPU and local temporary files only.

For a live run, fill `COST-PLAN.md` and `evidence/cost.json` before creating
capacity. Separate:

- estimated compute from observed or billed compute;
- on-demand from Spot assumptions;
- one-GPU from three-node wall time;
- training from evaluation and serving;
- image/model/index storage;
- volume/snapshot lifecycle;
- load balancer and data-transfer charges;
- telemetry ingestion/retention;
- idle node time during image/model load;
- intentionally retained post-capstone storage.

Set a hard GPU-hour limit and a wall-clock stop. A distributed run can consume
three times the node-hours while completing less work if communication stalls.
Stop on missing telemetry, repeated readiness failure, an unbounded queue,
unexpected node types, cost-alarm breach, or unintended exposure.

Never place credentials, account identifiers, private endpoints, raw restricted
prompts, or private documents in the repository or evidence shared publicly.
Use short-lived workload identity and an approved secret provider. Keep local
servers on loopback. Keep Kubernetes Services private until a supported
identity/authorization path has proved denial.

The wrapper in `scripts/run-step.sh` is plan-only by default. Execution requires
an explicit script beneath this repository’s `lessons/`, `--execute`, and a
typed `<project-id>:<step>` confirmation. It does not decide that a cloud
mutation is safe; the operator still reviews the named earlier-lesson script,
context, namespace, budget, and cleanup.

## Predict before running

Create `artifacts/predictions.md` outside the evidence workspace and answer:

1. Which model/precision fits one GPU with weights, KV cache, runtime
   allocations, and headroom?
2. If choosing three nodes, is tensor or pipeline parallelism more likely to
   dominate communication for your workload?
3. Which engine should win TTFT, output throughput, memory, and operability—and
   under exactly which workload?
4. Which optimization is most likely to change quality?
5. What is the first saturation signal?
6. How long from autoscaler decision to a ready model replica?
7. What failure should cause bounded rejection rather than an unbounded queue?
8. Can the optional adapter improve the frozen target without regressing a
   critical slice?
9. Does RAG improve grounded correctness enough to justify its latency and
   authorization surface?
10. Which response proves anonymous denial comes from the intended identity
    gate?
11. What is the known-good rollback release?
12. Which resource is most likely to survive Kubernetes deletion and continue
    costing money?

Preserve predictions and compare them with evidence. A wrong prediction is a
useful result; changing the prediction after measurement is not.

## Lab outline

1. Run the deterministic local verifier suite.
2. Initialize a no-overwrite operator workspace.
3. Define workload, SLO, quality gates, security boundary, budget, and rejected
   alternatives.
4. Pin model, tokenizer, image, engine, and configuration.
5. Choose one-GPU or three-node serving.
6. Add an optional adapter only if its frozen evaluation justifies it.
7. Add optional RAG only if its decision study and authorization model justify
   it.
8. Render and review private Kubernetes desired state.
9. Run predeclared evaluation and capacity studies.
10. Verify observability, autoscaling, access control, provenance, and threat
    controls.
11. Inject one bounded failure and recover.
12. Promote the immutable release and roll it back.
13. Reproduce with a second operator.
14. Tear down and prove the after-inventory is empty.
15. Bind hashes and run the strict operator completion gate.

## Step-by-step lab

### 1. Prove the verifier catches bad evidence

```bash
./scripts/run-local-lab.sh
```

The script first validates `fixtures/passing/`. It then applies each failure
overlay in memory; it never changes the fixture. Expect failures including:

```text
FABRICATED_LIVE_CLAIM
MODEL_IDENTITY_MISMATCH
QUALITY_EVIDENCE_MISSING
PUBLIC_EXPOSURE
UNVERIFIED_CLEANUP
```

Inspect one:

```bash
./scripts/run-deliberate-failure.sh \
  fixtures/failures/mismatched-model-revision.json
```

### 2. Initialize an operator workspace

Use an ignored path. The initializer refuses a nonempty target:

```bash
CAPSTONE_WORKSPACE="$PWD/artifacts/my-open-model-platform"
./scripts/init-workspace.sh "$CAPSTONE_WORKSPACE"
find "$CAPSTONE_WORKSPACE" -type f | sort
```

Run it a second time and confirm it exits nonzero without changing files:

```bash
./scripts/init-workspace.sh "$CAPSTONE_WORKSPACE"
```

Expected:

```text
output is not empty; no files were changed
```

Every `__...__` marker is deliberately unresolved. Do not run a global blind
replacement. Edit each field and understand its claim.

### 3. Write the architecture decision and boundaries

Fill `ADR.md`, `THREAT-MODEL.md`, `COST-PLAN.md`, and `RUNBOOK.md`. Start from
the diagrams in `docs/`.

In `contract.json`, choose:

```json
{
  "validation_mode": "operator-run",
  "claim_scope": "private staging in one region, frozen workload v1, selected hardware only",
  "serving_topology": "one-gpu",
  "features": {
    "adapter": false,
    "rag": false
  }
}
```

If choosing three nodes, set topology in contract, environment, release, and
serving configuration. Record exactly three nodes, one GPU per node, and a
model-splitting product `tensor_parallel_size × pipeline_parallel_size = 3`.

### 4. Pin the base model and tokenizer

Use the exact immutable revision previously validated in lessons 03 and 11.
Record the same ID/revision in:

- `contract.json`;
- `environment.json`;
- `release.json`;
- the rendered Kubernetes manifest;
- optional adapter base metadata;
- runtime identity evidence.

Resolve/download with the earlier lesson’s approved workflow. Record license,
remote-code policy, tokenizer/chat-template revision, file hashes/sizes, and
artifact location. Do not put cached weights in this repository.

Before continuing:

```bash
python3 -m json.tool "$CAPSTONE_WORKSPACE/contract.json" >/dev/null
python3 -m json.tool "$CAPSTONE_WORKSPACE/release.json" >/dev/null
```

### 5. Select and freeze the serving configuration

Use lessons 11–16 and 23. Begin with an engine baseline, then compare only
configurations that support the chosen model, topology, dtype/quantization,
adapter mode, and operational needs.

Fill `artifact-records/serving-config.json`. For a one-GPU example, the arithmetic is:

```json
{
  "tensor_parallel_size": 1,
  "pipeline_parallel_size": 1,
  "data_parallel_size": 1
}
```

For a three-node model split, valid teaching examples are TP=3/PP=1 or
TP=1/PP=3. Whether either engine supports the selected combination/version is a
separate preflight requirement. Record actual support; do not infer it from the
arithmetic.

Render/deploy scripts remain in their source lessons. Preview an invocation:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
./scripts/run-step.sh \
  --workspace "$CAPSTONE_WORKSPACE" \
  --step render \
  --script "$REPO_ROOT/lessons/phase-03-optimization/23-capstone-optimize-under-slo/scripts/render-deployment.sh"
```

The output says `execution=planned-only`. After reviewing the script and
arguments, execute only with the exact typed confirmation shown:

```bash
./scripts/run-step.sh \
  --workspace "$CAPSTONE_WORKSPACE" \
  --step render \
  --script "$REPO_ROOT/lessons/phase-03-optimization/23-capstone-optimize-under-slo/scripts/render-deployment.sh" \
  --execute \
  --confirm 'my-project-id:render' \
  -- --help
```

Replace the project ID and arguments; `--help` is shown because it is a safe
first execution. The wrapper never guesses a cluster or creates capacity.

### 6. Decide whether to adapt

If no adapter is justified, leave `features.adapter` and
`release.adapter.enabled` false. Keep `adapter_sha256: "not-produced"` and the
training revisions as `not-applicable`, fill the selected base revision and
license review, and record the retention decision in the ADR.

If enabled:

1. reuse the frozen dataset and evaluation lock from lessons 33–34;
2. train through lesson 35 or 36;
3. preserve training config, seed, package versions, raw logs, checkpoint
   lineage, and cost;
4. package through lesson 39;
5. record safetensors hash and exact base revision;
6. evaluate base and adapted variants on identical cases;
7. reject promotion if any critical gate regresses.

Do not copy training loss into `evidence/quality.json`. Quality evidence comes
from the frozen evaluation.

### 7. Decide whether to add RAG

If disabled, keep both artifact hashes and corpus/index versions as
`not-produced`, keep the embedding revision as `not-applicable`, and complete
the license/decision record.

If enabled:

1. record the lesson-40 decision;
2. freeze authorized corpus/source versions;
3. preserve deterministic chunker and embedding revisions;
4. build/version the index through lesson 41;
5. evaluate retrieval and reranking through lesson 42;
6. test grounding, citation, abstention, injection, and tenant negatives
   through lesson 43;
7. deploy/update/rollback the knowledge system through lesson 44;
8. bind the final corpus/index manifest into this release.

The runtime must expose safe index identity so smoke evidence can prove it
served the release’s version.

### 8. Freeze evaluation before final tuning

Fill `artifact-records/eval-dataset.json` with the dataset/case-manifest revision,
license review, split, count, and hash. Store sensitive cases in approved
storage and keep only safe metadata here.

Fill `evidence/quality.json` after running the unchanged evaluation:

```text
frozen dataset SHA
metric direction and threshold
baseline value
candidate value
critical safety cases passed / total
raw results SHA
observed command, actor, time, source
```

The verifier checks the dataset hash, threshold direction, baseline
non-regression for a higher-is-better metric, and all safety cases. Expand your
organization’s evaluator beyond this minimal scalar rule; retain per-case and
slice results.

### 9. Render private Kubernetes state

Once contract, environment, release image, model, and namespace are filled:

```bash
./scripts/render-private-manifest.sh \
  --workspace "$CAPSTONE_WORKSPACE" \
  --replace \
  --confirm 'my-project-id:render-private-manifest'
```

Expected:

```text
exposure=private
apply=not-performed
```

Inspect:

```bash
sed -n '1,280p' "$CAPSTONE_WORKSPACE/k8s/platform.yaml"
```

Run server-side dry-run only against the intended cluster after context review:

```bash
kubectl config current-context
kubectl apply --dry-run=server -f "$CAPSTONE_WORKSPACE/k8s/platform.yaml"
```

The checked renderer intentionally accepts only `one-gpu`; it refuses a
three-node contract rather than emitting a false single-Pod topology. Merge
engine-specific command, storage, node selectors, tolerations, probes, metrics,
and drain behavior from earlier lessons. Preserve private exposure and
restricted controls. For `three-node`, compose and review the selected
engine/operator-specific distributed resource, label it with
`oms.open-model.systems/serving-topology: three-node` and
`oms.open-model.systems/worker-count: "3"`, then retain rank/placement evidence.

### 10. Deploy and prove runtime identity

Use lesson 48’s immutable promotion flow and the selected engine/distributed
lesson. Preview before execution:

```bash
./scripts/run-step.sh \
  --workspace "$CAPSTONE_WORKSPACE" \
  --step deploy-private \
  --script "/absolute/path/to/repository/lessons/.../scripts/deploy-private.sh"
```

Then review current context, namespace, image digest, model revision, GPU
requests, Service type, NetworkPolicy, budget, and cleanup. Execute with:

```text
--execute --confirm '<project-id>:deploy-private'
```

Collect desired and runtime identity:

- release/source/GitOps revision;
- image ID and digest;
- model/tokenizer revision;
- adapter identity if enabled;
- index/corpus version if enabled;
- engine name/version/config hash;
- Pod UID, node, GPU type, driver/runtime versions;
- rank/world-size and network evidence for three nodes.

Do not label a `kubectl get` result as behavioral proof. Send frozen smoke and
identity requests through the private access path.

### 11. Collect performance, observability, and capacity evidence

Reuse lesson 45’s load generator/schema and lesson 12’s methodology. Fill
`evidence/performance.json` with the frozen workload hash, sample count,
predeclared TTFT/total-latency/error limits, observed values, input/output token
throughput, and raw-results hash.

Correlate:

```text
client raw requests
server completion logs
request/trace IDs
engine queue/running/waiting/KV-cache metrics
GPU memory/utilization/errors
Pod CPU/memory/restarts/readiness
node condition and provisioning events
```

Record warmup, cache state, arrival pattern, prompt/output distribution,
sampling, concurrency, and measurement window. If three-node, add collective
and worker-level telemetry.

Use lesson 46 to configure a bounded autoscaling/reliability policy. Demonstrate
backpressure and the measured cold-start path. Do not run HPA and KEDA against
the same target.

### 12. Pass the authentication and governance release gate

Fill `THREAT-MODEL.md` and use lesson 47’s provenance and Kubernetes checks.
Test through the real intended boundary:

```text
anonymous -> denied by identifiable auth gate
authenticated wrong action/tenant -> denied
authenticated allowed action/tenant -> succeeds
```

Repeat cross-tenant retrieval negatives if RAG is enabled. Verify prompt and
document text are absent from unrestricted logs. Verify workload identity has
only required artifact/telemetry access. Verify image/model/adapter/index
provenance and license review.

Record pass/fail and raw-result hash in `evidence/security.json`. Keep
`public_exposure: false`.

### 13. Inject failure, recover, promote, and roll back

Choose one bounded failure with a stated blast radius:

- terminate one model Pod;
- make one three-node worker unavailable;
- introduce a candidate with failed readiness;
- stop the metrics source and observe autoscaler fallback;
- promote an incompatible index/adapter only in an isolated candidate and
  prove the gate blocks it.

Before injection, record start conditions, stop criteria, rollback target, and
an operator ready to abort. Capture a timestamped timeline:

```text
steady -> fault -> detection -> traffic protection
       -> desired capacity -> ready capacity -> recovery
       -> rollback -> post-rollback smoke and denial tests
```

Fill `evidence/reliability.json`. Every listed sub-gate must be `pass`, including
reproduction by a second operator.

Promotion fields in `release.json` record candidate/production pass, known-good
release, equal rollback target, and immutable GitOps revision. Preserve lesson
48’s promotion history outside this compact workspace and reference it through
the raw evidence hash.

### 14. Record cost without mixing estimates and bills

Fill `evidence/cost.json`:

- explicit currency;
- positive budget and GPU-hour limits;
- estimate and inputs hash;
- observed amount and source;
- observed GPU-hours;
- billing-evidence hash.

The verifier requires estimate, observed spend, and observed GPU-hours to stay
within declared limits. If billing data is delayed, label the value as observed
metered estimate and update the final record when authoritative billing arrives;
do not call it billed.

### 15. Teardown and inventory

Inventory before removal. Preview each earlier cleanup script with
`run-step.sh --step teardown`; execute only after reviewing the exact scope and
typed confirmation.

After Kubernetes objects disappear, verify every associated layer. Example
categories:

```text
namespace workloads/services/jobs/operators
GPU Pods and load generators
node-group/provisioner desired capacity
instances and autoscaling groups
volumes, snapshots, filesystems
load balancers, target groups, addresses
object versions and multipart uploads
registry images intentionally retained
logs, metrics, traces, dashboards, retention
experiment-created identity/network objects
```

Fill `evidence/cleanup.json` only after the after-inventory is empty for the
declared scope. A resource intentionally retained belongs in the cost plan with
owner, reason, expiry, and continuing cost; it cannot be hidden from the
inventory.

### 16. Bind evidence and run the completion verifier

Set all six release gates and corresponding evidence statuses to `pass`. Remove
every unresolved marker. Then bind hashes:

```bash
./scripts/finalize-workspace.sh \
  --workspace "$CAPSTONE_WORKSPACE" \
  --confirm 'my-project-id:bind-evidence'
```

The finalizer refuses synthetic mode, missing files, symlinks, unresolved
markers, non-pass gates, and non-observed evidence. It updates release
artifact/evidence hashes and creates `evidence-index.json`. To intentionally
replace an existing index after a reviewed evidence change, add
`--replace-index`; the change creates a new release/evidence revision.

Write the verifier report **outside** the exact workspace:

```bash
python3 src/verify_capstone.py \
  --workspace "$CAPSTONE_WORKSPACE" \
  --require-operator-run \
  --json-report "$PWD/artifacts/my-open-model-platform-verification.json"
```

Only this output qualifies:

```text
RESULT pass mode=operator-run live_release_qualified=true
```

Any evidence change after finalization produces a hash failure. Investigate the
change; do not simply refresh hashes without review.

### 17. Perform the handoff

Give a second operator:

- repository revision;
- safe copy of the finalized evidence workspace;
- approved locations for large/private immutable artifacts and raw evidence;
- access prerequisites;
- cost and safety bounds;
- known-good release;
- runbook and teardown scope.

They run the CPU fixture suite, verify your operator workspace, reproduce the
private candidate, run smoke/denial/rollback checks, and remove their
environment. Record their observed result in the reliability evidence and
create a new evidence index.

## Deliberate failure

The checked failures are safe virtual mutations:

```bash
for fixture in fixtures/failures/*.json; do
  echo "=== $fixture"
  if python3 src/verify_capstone.py \
    --workspace fixtures/passing \
    --overlay "$fixture"; then
    echo "unexpected pass"
    exit 1
  fi
done
```

Study why each failure usually produces more than one violation. Changing the
model revision also breaks the file hash. Removing quality evidence breaks the
index, exact inventory, and release gate. Public exposure both removes the
required `ClusterIP` control and introduces a forbidden Service type. Defense
in depth should create multiple independent reasons to reject an unsafe
release.

Create two additional overlays:

1. change the adapter base revision;
2. claim `origin: synthetic` inside an operator-run copy.

Expected codes include `ADAPTER_BASE_MISMATCH` and
`OPERATOR_EVIDENCE_ORIGIN`.

For a live deliberate failure, use the bounded lesson-46/48 drill described in
your runbook. Never inject broad node, network, identity, or data deletion
failure into a shared or production environment for this course.

## Verification

Static and CPU verification:

```bash
find scripts -type f -name '*.sh' -exec bash -n {} +
python3 -m compileall -q src
find . -type f -name '*.json' -print0 |
  while IFS= read -r -d '' file; do
    python3 -m json.tool "$file" >/dev/null
  done
./scripts/run-local-lab.sh
git diff --check
```

Check the fixture index independently:

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path("fixtures/passing")
index = json.loads((root / "evidence-index.json").read_text())
for entry in index["entries"]:
    actual = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
    assert actual == entry["sha256"], entry["path"]
print(f"PASS: {len(index['entries'])} fixture hashes match")
PY
```

Operator completion:

```bash
python3 src/verify_capstone.py \
  --workspace "$CAPSTONE_WORKSPACE" \
  --require-operator-run
```

Also validate rendered Kubernetes with your installed schema/policy tools and
server-side dry-run. Static text checks in this lesson are intentionally
conservative teaching gates, not a Kubernetes parser, admission controller,
signature verifier, vulnerability scanner, or cloud security review.

## Troubleshooting

`FILE_MISSING` or `WORKSPACE_FILE_SET` means the contract, index, and directory
inventory disagree. Keep raw outputs outside the compact workspace or add a
reviewed required-file entry and rebuild the release.

`HASH_MISMATCH` means bytes changed after indexing. Inspect the diff or recover
the expected artifact. Do not normalize or regenerate blindly.

`MODEL_IDENTITY_MISMATCH` or `TOKENIZER_REVISION_MISMATCH` means one component
references another snapshot. Fix the source artifact, rerun evaluation, and
create a new release.

`ADAPTER_BASE_MISMATCH` means the adapter is not bound to the selected base.
Select the correct base or retrain/repackage; editing only the metadata is
invalid.

`QUALITY_THRESHOLD`, `PERFORMANCE_SLO`, or `COST_BUDGET_EXCEEDED` is a real
failed gate. Reject or redesign the candidate. Do not move the threshold after
seeing results without a new reviewed contract.

`FABRICATED_LIVE_CLAIM` means fixture evidence claimed live execution.
`OPERATOR_RUN_REQUIRED` means you attempted to complete with the teaching
fixture. Create and observe an operator-run workspace.

`PUBLIC_EXPOSURE` means the environment, evidence, or manifest admits a public
path. Restore private topology and repeat access tests.

`UNVERIFIED_CLEANUP`, `CLEANUP_NOT_EMPTY`, or
`RESIDUAL_BILLABLE_RESOURCES` means teardown is incomplete. Re-inventory the
specific cloud/Kubernetes layers and wait for asynchronous deletion.

The manifest renderer refuses to overwrite unless `--replace` and the exact
typed confirmation are present. The finalizer similarly refuses to replace an
existing index without `--replace-index`.

If `run-step.sh` refuses a script, use an absolute path beneath this
repository’s `lessons/`, make the reviewed script executable, and preview
without `--execute`. It intentionally rejects arbitrary external commands.

## Evidence to collect

Retain, with sensitive content protected:

- repository source commit and reviewed change;
- image digest, build provenance, SBOM, vulnerability/license decisions;
- base model and tokenizer ID/revision/license/files;
- engine version and complete serving configuration;
- GPU/node/driver/runtime/network topology;
- frozen workload and raw request results;
- frozen evaluation manifest, thresholds, per-case and slice outcomes;
- optional training dataset/config/seed/checkpoints/adapter hash and base bind;
- optional corpus/chunker/embedding/index lineage and retrieval/grounding
  evaluation;
- rendered desired state, GitOps revision, sync/runtime identity;
- anonymous, unauthorized, authorized, and cross-tenant test results;
- threat model, accepted residual risks, owners, expiry;
- request/trace-correlated logs, metrics, traces, engine/GPU/Pod/node evidence;
- capacity curve, autoscaler decisions, cold-start intervals, overload
  behavior;
- failure timeline, recovery, rollback, and post-rollback checks;
- estimate inputs, observed GPU-hours, cost source, budget result;
- before/actions/after teardown inventory;
- second-operator reproduction record;
- finalized release and evidence index;
- strict verifier JSON report.

Record hashes and immutable locations. Avoid copying private prompts/documents
into broadly accessible CI artifacts.

## Exercises

1. Create a three-node contract with TP=3 and explain why DP=3 would not split
   one oversized model.
2. Add an overlay that changes `release.image` to a mutable tag; require
   `MUTABLE_IMAGE`.
3. Add an overlay that changes one evidence `claim_scope`; require
   `EVIDENCE_SCOPE_MISMATCH`.
4. Extend performance evidence with p95 ITL and queue-wait limits.
5. Extend quality evidence to multiple slices with independent release gates.
6. Model a three-node worker loss and state whether the system can degrade or
   must reject all work.
7. Compare attached versus merged adapter releases, including rollback size and
   serving-engine compatibility.
8. Add a RAG corpus update and rollback while preserving tenant authorization.
9. Add a signed provenance verification result without treating signature as a
   quality or license decision.
10. Add a policy check that every container has resource requests/limits and a
    digest-pinned image.
11. Design a canary gate with stable/candidate identity, minimum sample count,
    stop conditions, and no restricted traffic before auth verification.
12. Extend cleanup inventory for the exact AWS resources your EKS path can
    create.
13. Have another learner review only the evidence workspace and list claims
    they cannot independently establish.
14. Change one file after finalization and explain every violation produced.
15. Write a short retrospective comparing predictions with observed results,
    including one rejected optimization.

See `solutions/SOLUTIONS.md` for evaluation criteria and example reasoning, not
copy-and-submit answers.

## Completion gate

The capstone is complete only when all are true:

- the CPU fixture suite passes;
- contract mode is `operator-run`;
- one exact source/image/model/tokenizer/configuration release is identified;
- one-GPU or three-node topology arithmetic and runtime placement are proved;
- optional adapter and RAG are either explicitly disabled or fully bound and
  evaluated;
- frozen quality and workload inputs predate final measurement;
- all six observed gates pass without unresolved markers;
- desired Kubernetes state is private, digest-pinned, and restricted;
- runtime identity matches promoted identity;
- anonymous and unauthorized requests are denied by the intended gate;
- telemetry correlates requests through engine, GPU, Pod, and node layers;
- capacity/autoscaling boundaries and overload behavior are documented;
- a bounded failure recovers and a known-good rollback succeeds;
- a second operator reproduces the lifecycle;
- the cost remains within declared budget;
- teardown after-inventory is empty and no unintended billable capacity
  remains;
- finalization binds every required byte;
- this command succeeds:

```bash
python3 src/verify_capstone.py \
  --workspace "$CAPSTONE_WORKSPACE" \
  --require-operator-run
```

The final line must be:

```text
RESULT pass mode=operator-run live_release_qualified=true
```

A well-supported “do not promote this model” result can still demonstrate
excellent engineering, but it does not satisfy this platform-release completion
gate until a candidate passes. Preserve rejected studies as evidence.

## Cleanup

The local fixture suite removes its temporary directory automatically. Your
operator workspace lives under ignored `artifacts/`; keep the finalized safe
metadata only as long as needed. Remove private raw evidence according to its
retention policy, not with an unreviewed recursive command.

For the live platform:

1. stop load generators and background port-forwards;
2. move the environment pointer to the approved state or remove it;
3. delete only the capstone’s namespaced/workload resources with reviewed
   earlier-lesson cleanup scripts;
4. wait for Pods, Jobs, Services, endpoints, volumes, and operators to finish;
5. return GPU node/provisioner desired capacity to the recorded baseline;
6. verify instances and accelerators are gone;
7. verify load balancers, target groups, volumes, snapshots, filesystems,
   addresses, and object versions;
8. apply registry/model/index/log retention decisions;
9. capture the after-inventory;
10. investigate every residual and update cost ownership;
11. finalize cleanup evidence and rerun the strict verifier.

Do not destroy a shared cluster or shared node group merely because the
capstone used it. “Released GPU capacity” means return resources created or
raised for this experiment to the recorded starting state.

## Primary references

Primary sources reviewed 2026-10-21:

- Kubernetes, [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/),
  [Services](https://kubernetes.io/docs/concepts/services-networking/service/),
  [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/),
  [Probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/),
  [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/),
  [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/),
  and [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).
- AWS, [Amazon EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
  and [EKS IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html).
- NVIDIA, [NCCL user guide](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
  and [DCGM Exporter](https://docs.nvidia.com/datacenter/cloud-native/gpu-telemetry/latest/dcgm-exporter.html).
- vLLM, [distributed serving](https://docs.vllm.ai/en/latest/serving/distributed_serving.html)
  and [production metrics](https://docs.vllm.ai/en/latest/design/metrics.html).
- PyTorch, [Fully Sharded Data Parallel](https://docs.pytorch.org/docs/stable/fsdp.html)
  and [DistributedDataParallel](https://docs.pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html).
- Hugging Face, [Hub security](https://huggingface.co/docs/hub/security),
  [repository revisions](https://huggingface.co/docs/huggingface_hub/guides/download#download-a-single-file),
  [PEFT checkpoint format](https://huggingface.co/docs/peft/developer_guides/checkpoint),
  and [safetensors](https://huggingface.co/docs/safetensors/).
- Argo CD, [declarative setup](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)
  and [automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).
- OpenTelemetry, [specification](https://opentelemetry.io/docs/specs/otel/)
  and [semantic conventions](https://opentelemetry.io/docs/specs/semconv/).
- Prometheus, [instrumentation practices](https://prometheus.io/docs/practices/instrumentation/)
  and [alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/).
- SLSA, [provenance](https://slsa.dev/spec/v1.2/provenance) and Sigstore,
  [Cosign verification](https://docs.sigstore.dev/cosign/verifying/verify/).
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
  and [Secure Software Development Framework](https://csrc.nist.gov/Projects/ssdf).
- SPDX, [specifications](https://spdx.dev/use/specifications/) and OCI,
  [image specification](https://github.com/opencontainers/image-spec).

Versioned tool behavior changes. Recheck the documentation for the exact engine,
Kubernetes, EKS, autoscaler, GitOps, and security-policy versions in your
release; preserve the reviewed version and date in evidence.
