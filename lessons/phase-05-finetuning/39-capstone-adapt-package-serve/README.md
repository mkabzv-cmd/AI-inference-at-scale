# 39 — Capstone: adapt, package, and serve

**Status:** draft
**Time:** 14–20 hours
**Compute:** `local-cpu` for release integrity; optional `g1`, with `g3` only for a justified lesson-38 study
**GPU budget:** zero for the required path; separately budget training, evaluation, serving, and benchmark windows
**Prerequisites:** 32–38; lesson 38 is optional when the chosen adaptation fits one GPU
**Last reviewed:** 2026-10-21

## Why this matters

Fine-tuning is not complete when a training process writes weights. A usable
artifact must remain bound to the exact base model, tokenizer, chat template,
dataset, training configuration, evaluation contract, serving runtime, and
deployment manifest. Another learner should be able to reproduce what you did,
tell whether bytes changed, run the same acceptance checks, compare the same
benchmark workload, and roll back to a known previous release.

This capstone connects every part of the phase:

```text
lesson 33 frozen data
  + lesson 34 frozen evaluation
  + lesson 35 training lifecycle
  + lesson 36 full/LoRA/QLoRA decision
  + lesson 37 controlled performance evidence
  + optional lesson 38 distributed strategy
        |
        v
immutable release -> private serving -> evaluation -> benchmark -> rollback
```

The required CPU lab packages a deliberately nondeployable adapter fixture. It
hashes cards, tokenizer/base metadata, adapter configuration, and fixture
weights; verifies exact base/tokenizer/adapter binding; then mutates adapter
rank and proves that verification fails. The manifest says
`artifact_type: course-fixture` and `deployable: false`, so no one can mistake
JSON for model tensors.

The real capstone points the same builder at PEFT safetensors from lesson 36 or
a properly saved full/merged artifact. It reruns lesson 34's unchanged
acceptance set and lesson 12's `oms-benchmark/v1` workload on both base and
tuned endpoints. A strict verifier requires package integrity, a passing tuned
release decision, matching benchmark workloads, the same engine
version/configuration and GPU model, and exact base revision provenance.

The aim is not to guarantee that the tiny course adaptation passes. A valid
capstone can conclude “do not release,” provided the evidence and cleanup are
complete. Changing the gate after seeing failure is not completion.

## Learning outcomes

By the end, you can:

- choose full SFT, LoRA, or QLoRA from memory, quality, artifact, and serving
  requirements;
- distinguish a training checkpoint, adapter, merged model, and release bundle;
- bind an adapter to exact base and tokenizer revisions;
- include data and model cards without overstating capability;
- hash every release file and detect post-package mutation;
- mark fixtures and incomplete bundles as nondeployable;
- preserve the frozen evaluation lock and raw responses;
- compare base and tuned artifacts under one `oms-benchmark/v1` workload;
- distinguish correctness/quality gates from performance metrics;
- serve a named LoRA adapter with a Phase-2 engine;
- keep Kubernetes access private through ClusterIP and port-forward;
- resolve images to immutable digests before deployment;
- verify a rollback from an archived immutable manifest;
- prove cleanup across Kubernetes, storage, and GPU node capacity;
- hand another learner enough evidence to reproduce or reject the release.

## What you will build

The CPU path creates `artifacts/fixture-release/` containing:

- `release-manifest.json`;
- `release-config.json`;
- base architecture metadata;
- tokenizer metadata;
- adapter configuration;
- an explicit non-tensor fixture weight description;
- the lesson 33 data card;
- a model card;
- byte count and SHA-256 for every included file.

`verify_release.py` checks every declared path and hash, confirms the adapter's
base ID/revision matches the release, confirms tokenizer ID/revision matches the
base snapshot, and rejects a nondeployable fixture unless
`--allow-fixture` is explicitly supplied.

For the real path, you will build a deployable bundle, then produce:

- base and tuned frozen-evaluation results and raw responses;
- a passing or failing tuned release decision;
- base and tuned `oms-benchmark/v1` JSON;
- a strict cross-artifact verification report;
- a rendered private vLLM Deployment;
- an immutable previous manifest and rollback proof;
- a final model card, data card, release note, cost record, and cleanup record.

The included K8s template mounts the exact base snapshot and release from
read-only claims, enables a named LoRA adapter, requests one GPU, exposes only a
ClusterIP Service, and uses an immutable engine image reference.

## Files in this lesson

```text
39-capstone-adapt-package-serve/
├── README.md
├── MODEL_CARD.template.md
├── configs/
│   └── release.json
├── fixtures/
│   ├── adapter/
│   │   ├── adapter_config.json
│   │   ├── training-provenance.json
│   │   └── adapter_weights.fixture.json
│   └── base/
│       ├── config.json
│       ├── snapshot.json
│       └── tokenizer_config.json
├── k8s/
│   └── serve-adapter.yaml.tpl
├── schemas/
│   └── release-manifest.schema.json
├── scripts/
│   ├── cleanup.sh
│   ├── deploy-private.sh
│   ├── render-k8s.py
│   ├── rollback.sh
│   ├── run-acceptance.sh
│   ├── run-benchmark.sh
│   ├── run-cpu-lab.sh
│   └── run-deliberate-failure.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── build_release.py
    ├── verify_capstone.py
    └── verify_release.py
```

Generated release files, weights, raw responses, benchmarks, and rendered
manifests belong under ignored `artifacts/`.

## Under the hood

### Choose adaptation before selecting a favorite tool

Full SFT updates all selected model parameters and can offer maximum adaptation
capacity, but usually has the largest training/checkpoint footprint. LoRA
updates small low-rank matrices over a higher-precision frozen base. QLoRA
stores that frozen base in a quantized representation during training.

Use a decision table:

| Question | Full SFT | LoRA | QLoRA |
|---|---|---|---|
| Does ordinary full training state fit? | required | not required | not required |
| Small independently versioned artifact? | no | yes | yes |
| Shared base for multiple adapters? | no | yes | yes |
| Quantized-base training complexity? | no | no | yes |
| Engine supports attached adapter? | not needed | required unless merged | required unless merged |
| Merge needs nonquantized exact base? | n/a | recommended controlled path | required by course policy |

The answer comes from lesson 34 quality, lesson 35 correctness, lesson 36
candidate evidence, and lesson 37 resource measurements. Distributed training
is justified only when a chosen model/state requires it or the experiment
explicitly studies scaling.

### Artifact layers

A training checkpoint may contain optimizer/scheduler/RNG state and is useful
for resume. A serving artifact usually needs model or adapter tensors,
configuration, tokenizer, generation defaults, and provenance, not training
optimizer state. A release bundle adds cards, evaluation, benchmark, manifest,
image/deployment identity, and rollback instructions.

An adapter cannot stand alone:

```text
behavior = exact base revision
         + exact tokenizer/chat template
         + exact adapter bytes/config
         + engine loading semantics
         + decoding request
```

Loading over a mutable tag or similarly named base is not reproducible.

### Manifest integrity

The release builder copies declared metadata/cards and adapter files, then
records path, size, and SHA-256 for every file. It also records:

- release and adaptation names;
- base model ID, revision, and license;
- tokenizer ID and revision;
- dataset contract and manifest hash;
- training configuration hash;
- evaluation contract and lock hash;
- release-gates file hash;
- benchmark contract;
- deployable versus fixture status.

The manifest itself is the root record and should be stored immutably or signed
in a production extension. A hash detects change only when the trusted expected
hash or signature is kept elsewhere. Rebuilding a manifest after unexplained
mutation does not restore integrity.

### Cards are claims with boundaries

The data card documents source, license, transformation, split, limitations,
and prohibited uses. The model card states base/adaptation, intended use,
training, evaluation, limitations, and reproducibility. It must not claim broad
Kubernetes expertise from twelve training conversations and eight acceptance
items.

Include failed slices and known metric disagreements. “Passes the course
acceptance set” is narrower and more honest than “safe.”

### Attached versus merged serving

An attached LoRA adapter lets one engine share a base and load named adapters.
It adds runtime adapter support and potentially request-level routing. A merged
artifact applies `W + sBA` offline and loads like an ordinary model, but is
larger and duplicates base weights.

For QLoRA, reload the exact base at intended serving precision before merge.
After any merge:

- save new safetensors and config;
- record transformation code/version and input hashes;
- compare attached versus merged deterministic logits/outputs;
- repeat frozen evaluation;
- repeat performance benchmark;
- treat it as a new release artifact.

### Quality and performance are different gates

Lesson 34 determines whether behavior clears predeclared requirements. Lesson
12 measures serving performance under `oms-benchmark/v1`. A fast model with a
forbidden safety claim cannot be promoted. A correct model that misses an SLO
may also be unsuitable, but the remediation differs.

The strict verifier checks:

1. deployable package and file integrity;
2. same frozen evaluation contract, acceptance/config hashes, raw-prediction
   hashes, item IDs, and example count, with both results recomputed from the
   checked raw prediction files;
3. the release-gates file hash matches package provenance, and every tuned
   release check is recomputed from those gates;
4. tuned release decision is true;
5. both benchmarks pass lesson 12's validator, use `oms-benchmark/v1`, and
   contain no failed requests;
6. workload objects are exactly equal;
7. engine name, version, config, client, image fingerprint, and GPU match;
8. base and adapter aliases match release provenance;
9. benchmark base revision matches release provenance.

It does not decide what latency/SLO threshold your organization needs. Declare
that before measurement and add it as a versioned gate.

### Private serving and rollout

The template uses vLLM's LoRA serving flags:

```text
--model /models/base
--enable-lora
--lora-modules oms-operations=/release/adapter
```

The Service is `ClusterIP`; the lab reaches it with `kubectl port-forward`.
There is no LoadBalancer, Ingress, or public authentication claim. The model
and release volumes are read-only. A startup probe allows model loading; a
readiness probe controls endpoints. The model Pod accepts only same-namespace
traffic on its API port and has no allowed egress; verify that the cluster's
network-policy implementation enforces those rules. The image must support
UID/GID 10001; writable cache/home paths are under `/tmp`, while model and
release claims remain read-only and must already be readable by that identity.
The policy is applied before the Deployment is created.

The Deployment uses `Recreate` because one-GPU capacity may not fit old and new
Pods simultaneously. That creates downtime. A production rollout needs enough
capacity for surge/canary, authenticated traffic, rate limits, observability,
and an independently tested rollback.

### Rollback is a known forward action

Keep the previous rendered manifest with immutable image digest and volume
identities, previous release manifest, and acceptance decision. Rollback
reapplies those known bytes. Then verify health, served model list, deterministic
smoke response, acceptance subset/full suite, and image/release hashes.

`kubectl rollout undo` alone can be ambiguous if external mutable volumes or
tags changed. The checked script requires an archived manifest containing a
digest.

## Prerequisites and preflight

Run the CPU path from this directory:

```bash
cd lessons/phase-05-finetuning/39-capstone-adapt-package-serve
python3 --version
python3 -m json.tool configs/release.json >/dev/null
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Before the real path, require:

- lesson 33 dataset manifest and approved data card;
- lesson 34 acceptance lock, base raw responses, result, and decision;
- lesson 35 complete training/resume evidence;
- lesson 36 real safetensors adapter or documented full artifact;
- lesson 37 controlled resource comparison;
- lesson 38 only if used, with checkpoint/recovery evidence;
- exact model/tokenizer snapshot in an approved read-only location;
- a Phase-2 engine image resolved to digest;
- enough one-GPU node capacity for serving;
- current identity/context/capacity and a bounded test window.

Verify no fixture file is entering the real release. Run
`verify_release.py` without `--allow-fixture`; that is the important difference.

## Cost and safety

The required package lab is offline and uses tiny text files. It creates no
deployable model.

The optional capstone can incur:

- training GPU time;
- model/evaluation/benchmark GPU time;
- persistent model and release volumes;
- container registry storage and transfer;
- snapshots or object-store versions;
- logs and metrics;
- idle nodes after Pods finish.

Budget each window independently. Reuse the same warmed environment for base
and tuned performance only if the benchmark contract says so. Stop when a
quality gate fails; do not pay for a large benchmark of an ineligible release.

Keep the endpoint private. ClusterIP plus port-forward is the lab default.
Never place private training examples, cloud credentials, registry tokens, or
cluster metadata in cards or manifests. Adapter weights can memorize source
data and require the same access control as full weights.

The Kubernetes scripts require explicit guard variables and immutable images.
They do not scale GPU nodes automatically.

## Predict before running

Create `artifacts/predictions.md`:

1. Can the CPU fixture be served?
2. Which three exact identities must an adapter bind together?
3. Does changing `adapter_config.json` require a new manifest?
4. Can a tuned model be promoted if benchmark latency improves but a forbidden
   claim appears?
5. Must base and tuned benchmark workloads be byte-for-byte equivalent?
6. Why can an engine version change invalidate performance comparison?
7. What additional evidence does a merged QLoRA artifact require?
8. Does a successful rollout prove the correct adapter is active?
9. Which external resources may remain after namespace deletion?
10. What exact artifact will you reapply for rollback?

## Lab outline

1. Build and inspect the nondeployable CPU release fixture.
2. Verify every file hash and base/tokenizer/adapter binding.
3. Mutate adapter rank and prove tamper detection.
4. Select full, LoRA, or QLoRA from prior evidence.
5. Build a deployable release from real safetensors.
6. Serve base and tuned artifacts privately through one Phase-2 engine.
7. Run the unchanged lesson 34 evaluation on both.
8. Run identical `oms-benchmark/v1` workloads on both.
9. Execute the strict capstone verifier.
10. Roll back from an immutable archived manifest and clean up.

## Step-by-step lab

### 1. Build the integrity fixture

```bash
./scripts/run-cpu-lab.sh
python3 -m json.tool artifacts/fixture-release/release-manifest.json
```

Expected:

```text
PASS: built course-fixture release with 9 hashed files
PASS: verified 9 hashes and exact base/tokenizer/adapter binding
PASS: nondeployable CPU fixture exercises release hashing and binding
```

Confirm:

```bash
python3 - <<'PY'
import json
from pathlib import Path

m = json.loads(
    Path("artifacts/fixture-release/release-manifest.json").read_text()
)
assert m["artifact_type"] == "course-fixture"
assert m["deployable"] is False
assert m["benchmark_contract"] == "oms-benchmark/v1"
print("PASS: fixture cannot be mistaken for a deployable adapter")
PY
```

Read the model and data cards. List claims that remain unsupported.

### 2. Build a real adapter release

Use the selected lesson 36 adapter. Compute actual hashes:

```bash
dataset_manifest="../33-dataset-engineering-chat-templates/artifacts/dataset/manifest.json"
training_config="../36-lora-qlora/artifacts/lora-r8/effective-config.json"
evaluation_lock="../34-evaluation-before-optimization/acceptance.lock.json"
release_gates="../34-evaluation-before-optimization/configs/release-gates.json"

sha256_file() {
  python3 -c \
    'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
    "$1"
}
dataset_sha="$(sha256_file "$dataset_manifest")"
training_sha="$(sha256_file "$training_config")"
evaluation_sha="$(sha256_file "$evaluation_lock")"
release_gates_sha="$(sha256_file "$release_gates")"

python src/build_release.py \
  --config configs/release.json \
  --base-metadata-dir "<exact-tokenizer-config-and-snapshot-metadata-directory>" \
  --adapter-dir ../36-lora-qlora/artifacts/lora-r8/adapter \
  --data-card ../33-dataset-engineering-chat-templates/DATA_CARD.md \
  --model-card MODEL_CARD.template.md \
  --dataset-manifest-sha256 "$dataset_sha" \
  --training-config-sha256 "$training_sha" \
  --evaluation-lock-sha256 "$evaluation_sha" \
  --release-gates-sha256 "$release_gates_sha" \
  --output artifacts/release

python src/verify_release.py --release artifacts/release
```

Do not pass `--fixture`. The builder requires a safetensors adapter and the
verifier requires `deployable: true`. The base metadata directory must contain
`config.json`, `tokenizer_config.json`, and a reviewed `snapshot.json` with
`model_id`, `model_revision`, `tokenizer_id`, and `tokenizer_revision`. Generate
that record while resolving the immutable snapshot; do not infer a commit from
a mutable cache name. The lesson-36 trainer also writes
`adapter/training-provenance.json`; the release verifier binds its base,
dataset, effective-config, rank, alpha, and targets to the release and PEFT
configuration.

### 3. Stage exact model and release volumes

Copy the exact pinned base snapshot and verified release to approved claims.
Verify hashes after the copy. Ensure claims are read-only in the serving Pod.
Record retention/reclaim policy and ownership.

Resolve a compatible vLLM image to a digest. Preserve engine version and flags.
Then:

```bash
export IMAGE_REF="<registry>/vllm-openai@sha256:<digest>"
export GPU_INSTANCE_TYPE="g5.xlarge"
export MODEL_CLAIM="<exact-base-snapshot-claim>"
export RELEASE_CLAIM="<verified-release-claim>"
export ALLOW_LESSON_39_DEPLOY=yes
./scripts/deploy-private.sh
```

The script ends with port-forward in the foreground. In another terminal:

```bash
curl -fsS http://127.0.0.1:8000/v1/models | python3 -m json.tool
```

Verify both the base and named `oms-operations` adapter are represented as
expected by your engine version. Send one deterministic smoke request with the
exact frozen decoding fields.

### 4. Evaluate base and tuned behavior

Serve the base treatment with the same engine/image/flags except adapter
activation, then:

```bash
export MODEL_BASE_URL=http://127.0.0.1:8000
export MODEL_ID="Qwen/Qwen2.5-0.5B-Instruct"
./scripts/run-acceptance.sh base
```

Switch to the named adapter without changing the frozen evaluation:

```bash
export MODEL_ID="oms-operations"
./scripts/run-acceptance.sh tuned
```

The tuned script invokes the release gates with `--require-pass`. If it fails,
the correct capstone result is no release. Keep raw responses and diagnose.

### 5. Benchmark equal treatments

Set exact engine and environment fields, then run base and tuned:

```bash
export BENCH_BASE_URL=http://127.0.0.1:8000
export ENGINE_NAME=vllm
export ENGINE_VERSION="<exact-version>"
export ENGINE_CONFIG_JSON='{"max_model_len":2048,"enable_lora":true}'
export SERVER_FINGERPRINT="$IMAGE_REF"
export BENCH_GPU_NAME="<exact-nvidia-smi-name>"
export MODEL_REVISION=7ae557604adf67be50417f59c2c2f167def9a775

export MODEL_ID="Qwen/Qwen2.5-0.5B-Instruct"
./scripts/run-benchmark.sh base
export MODEL_ID="oms-operations"
./scripts/run-benchmark.sh tuned
```

Both outputs use `oms-benchmark/v1`. The capstone does not prescribe that the
tuned adapter must be faster; it requires an honest comparison.

### 6. Run the strict cross-artifact gate

```bash
python src/verify_capstone.py \
  --release artifacts/release \
  --base-evaluation artifacts/evaluation-base/endpoint-results.json \
  --tuned-evaluation artifacts/evaluation-tuned/endpoint-results.json \
  --acceptance ../34-evaluation-before-optimization/data/acceptance.jsonl \
  --evaluation-config ../34-evaluation-before-optimization/configs/evaluation.json \
  --base-predictions artifacts/evaluation-base/endpoint-predictions.jsonl \
  --tuned-predictions artifacts/evaluation-tuned/endpoint-predictions.jsonl \
  --tuned-decision artifacts/evaluation-tuned/required-pass-decision.json \
  --evaluation-lock ../34-evaluation-before-optimization/acceptance.lock.json \
  --release-gates ../34-evaluation-before-optimization/configs/release-gates.json \
  --base-benchmark artifacts/benchmark/base.json \
  --tuned-benchmark artifacts/benchmark/tuned.json \
  --output artifacts/capstone-verification.json
```

Expected only when every condition passes:

```text
PASS: package, frozen evaluation, and benchmark evidence agree
```

### 7. Roll back

Before deployment, archive the previous rendered manifest and its release
manifest. To test rollback:

```bash
export ROLLBACK_MANIFEST="artifacts/previous-serve-manifest.yaml"
export ALLOW_LESSON_39_ROLLBACK=yes
./scripts/rollback.sh
```

After rollout, rerun health, `/v1/models`, one deterministic request, and the
approved acceptance checks. Record restoration time and any request failures.

## Deliberate failure

Run immediately after the CPU lab:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-tamper-failure.txt
```

The script changes adapter rank from 8 to 64 inside the packaged directory.
The manifest still contains the original file size/hash, so verification fails
with `artifact hash mismatch`.

Recovery for the fixture is to rerun `run-cpu-lab.sh`. In a real release, first
determine why bytes changed. If the change is intentional, create a new release
name with new training/evaluation evidence and store the old manifest. Do not
regenerate a hash in place and call the old release unchanged.

Additional deliberate failures:

- pass the fixture to `verify_release.py` without `--allow-fixture`;
- evaluate tuned responses under a modified acceptance file;
- benchmark tuned at different concurrency or max tokens;
- change engine version between base and tuned;
- remove one adapter safetensors file;
- attempt rollback with a mutable image tag.

Each must fail before promotion.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 src/verify_release.py \
  --release artifacts/fixture-release \
  --allow-fixture
```

For a real release:

```bash
python3 src/verify_release.py --release artifacts/release
python3 src/verify_capstone.py \
  --release artifacts/release \
  --base-evaluation artifacts/evaluation-base/endpoint-results.json \
  --tuned-evaluation artifacts/evaluation-tuned/endpoint-results.json \
  --acceptance ../34-evaluation-before-optimization/data/acceptance.jsonl \
  --evaluation-config ../34-evaluation-before-optimization/configs/evaluation.json \
  --base-predictions artifacts/evaluation-base/endpoint-predictions.jsonl \
  --tuned-predictions artifacts/evaluation-tuned/endpoint-predictions.jsonl \
  --tuned-decision artifacts/evaluation-tuned/required-pass-decision.json \
  --evaluation-lock ../34-evaluation-before-optimization/acceptance.lock.json \
  --release-gates ../34-evaluation-before-optimization/configs/release-gates.json \
  --base-benchmark artifacts/benchmark/base.json \
  --tuned-benchmark artifacts/benchmark/tuned.json \
  --output artifacts/capstone-verification.json
```

Also independently:

- recompute all manifest file hashes;
- compare model/tokenizer revision with the mounted snapshot;
- verify Pod image ID contains the declared digest;
- inspect `/v1/models` and one raw request;
- review every failed acceptance response;
- validate benchmark results with lesson 12's validator;
- apply and verify rollback;
- confirm Kubernetes, storage, and GPU capacity cleanup.

## Troubleshooting

If a real package is marked nondeployable, ensure you omitted `--fixture` and
the adapter directory contains actual safetensors. Never rename JSON to
`.safetensors`.

If adapter/base binding fails, inspect PEFT configuration and training
provenance. The checked trainer writes the immutable base commit to PEFT's
standard `revision` field, and the verifier also understands the older course
fixture alias. Do not edit the adapter config to match a different base.

If tokenizer identity fails, copy the exact tokenizer snapshot from training.
A tokenizer with the same model ID but a different mutable revision can change
IDs and chat formatting.

If vLLM does not list or load the adapter, inspect engine version, LoRA support,
adapter path, read-only mount permissions, PEFT type/targets/rank limits, and
base compatibility. Preserve startup logs.

If readiness never passes, separate image pull, volume mount, CUDA allocation,
model load, adapter load, and HTTP health. Startup probe should absorb
legitimate load time; liveness is intentionally absent from the draft to avoid
restart loops during diagnosis.

If acceptance results differ across repeats at temperature zero, compare engine
version/config, batching, precision, kernels, request bytes, model/adapter
identity, and returned model field. Report variance.

If the capstone verifier says workload differs, diff the complete workload
objects. Do not copy fields between result files.

If rollback starts but behavior remains tuned, verify mounted release content,
engine flags, Pod image ID, rollout revision, and response model selection.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── fixture-release/
├── expected-tamper-failure.txt
├── release/
│   ├── release-manifest.json
│   ├── release-config.json
│   ├── MODEL_CARD.md
│   ├── DATA_CARD.md
│   ├── base-metadata/
│   └── adapter/
├── evaluation-base/
├── evaluation-tuned/
├── benchmark/
│   ├── base.json
│   └── tuned.json
├── serve-adapter.yaml
├── previous-serve-manifest.yaml
├── capstone-verification.json
├── rollback-report.md
├── cleanup-report.md
└── final-report.md
```

`final-report.md` must state why adaptation was needed, selected method,
rejected candidates, all immutable identities/hashes, cards, training
correctness, base/tuned quality by slice, forbidden claims, base/tuned
performance with equal workload, costs, limitations, release/no-release
decision, rollback result, and cleanup proof.

## Exercises

1. Sign the release manifest with an approved keyless provenance workflow.
2. Extend the verifier to check tokenizer file hashes against training evidence.
3. Package and compare attached versus merged LoRA releases.
4. Add a QLoRA merge transformation manifest.
5. Serve two adapters over one base and test request isolation.
6. Add a canary Deployment with enough temporary GPU capacity.
7. Define an SLO gate before running the benchmark.
8. Add software-bill-of-materials and image-signature verification.
9. Test rollback while requests are in flight.
10. Rescore historical raw responses under a new metric without changing the
    old result.
11. Add an artifact revocation record for a data-deletion request.
12. Have another learner reproduce the package from manifests alone.

## Completion gate

You are done when:

- the CPU fixture is clearly nondeployable and its tamper drill fails;
- the chosen adaptation method is justified by prior measured evidence;
- the real package contains actual tensors, exact tokenizer metadata, cards,
  and immutable hashes;
- `verify_release.py` passes without fixture permission;
- base and tuned models use the unchanged frozen evaluation contract;
- the tuned release passes every predeclared gate, or the final decision is
  explicitly no release;
- base and tuned `oms-benchmark/v1` workloads and engine/GPU conditions match;
- the strict capstone verifier passes for any promoted release;
- the private ClusterIP endpoint proves the correct adapter is active;
- an archived immutable rollback manifest restores known behavior;
- another learner can reproduce or reject the release from collected evidence;
- Kubernetes, storage, registry policy, and GPU node capacity are verified
  after cleanup.

## Cleanup

For generated local fixtures and evidence after approved retention:

```bash
rm -rf -- artifacts
```

For the serving namespace:

```bash
export ALLOW_LESSON_39_CLEANUP=yes
./scripts/cleanup.sh
```

Then verify model/release PVC reclaim policy, PVs, snapshots, object-store
versions, registry images, logs, and GPU node-group capacity. Retain only
approved immutable releases and audit evidence. Rejected artifacts containing
private training data need governed deletion, not casual local removal.

Do not delete the previous release/rollback evidence until the new release is
formally retired. Do not leave a completed Pod as proof that an instance has
scaled down.

## Primary references

Sources were reviewed on 2026-10-21:

- [Hugging Face model cards](https://huggingface.co/docs/hub/en/model-cards)
- [Hugging Face dataset cards](https://huggingface.co/docs/hub/en/datasets-cards)
- [PEFT checkpoint format](https://huggingface.co/docs/peft/main/en/developer_guides/checkpoint)
- [PEFT model merging](https://huggingface.co/docs/peft/main/en/developer_guides/model_merging)
- [vLLM LoRA documentation](https://docs.vllm.ai/en/latest/features/lora/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [SLSA provenance specification](https://slsa.dev/spec/v1.1/provenance)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The CPU release builder, verifier, and tamper failure are author-validated. The
strict capstone verifier and Kubernetes serving/rollback paths are
syntax/configuration-validated but have not been exercised against a live GPU,
engine, registry, PVC, or EKS cluster in this draft.
