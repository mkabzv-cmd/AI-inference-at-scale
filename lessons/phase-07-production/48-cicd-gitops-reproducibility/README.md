# 48 — CI/CD, GitOps, and reproducibility

**Status:** draft
**Time:** 8–14 hours
**Compute:** `local-cpu`; optional bounded `g1` smoke environment
**GPU budget:** zero locally; one short smoke window only after CPU gates pass
**Prerequisites:** 39, 44–47
**Last reviewed:** 2026-10-21

## Why this matters

An ordinary service release is already more than source code. An open-model
release may include:

- application source and container image;
- CUDA/native dependencies and engine version;
- base model and tokenizer revisions;
- quantization representation;
- adapter bytes and the exact base revision they target;
- retrieval corpus/index version;
- generation and scheduler configuration;
- quality, retrieval, performance, and security evidence;
- Kubernetes/GitOps state.

Promoting only `image: v7` can combine a new image with an old adapter, mutable
model tag, incompatible tokenizer, stale index, or failed evaluation. The
deployment may start and still be the wrong system.

This lesson defines the release as one immutable compatibility contract. A
local pipeline validates it, renders a private digest-pinned Kubernetes
workload, promotes it to an atomic staging pointer, starts a loopback smoke
service, verifies runtime identity and behavior, and only then promotes the
same contract to production.

Two negative candidates teach different gates:

- `candidate-invalid.json` is structurally and cryptographically invalid and
  declares a failed quality gate;
- `candidate-regression.json` has valid immutable metadata and passing declared
  gates but returns unsafe, incorrect smoke behavior.

The second candidate reaches staging, fails behavior, never changes production,
and is rolled back. This demonstrates why schemas, provenance, policy, and
runtime tests are complementary.

## Learning outcomes

By the end, you can:

- define the complete model-platform release unit;
- bind source, image, model, tokenizer, adapter, index, configuration, and
  evidence by immutable identifiers;
- enforce adapter/base and model/tokenizer compatibility;
- distinguish build, validation, deployment, smoke, promotion, and rollback;
- render desired Kubernetes state from one release contract;
- use compare-and-swap to detect environment drift before promotion;
- keep an append-only promotion history;
- prove runtime release identity rather than trusting desired state alone;
- run a behavioral smoke gate in addition to health;
- contain a regression in staging and restore the previous release;
- explain pull-based GitOps reconciliation and drift;
- separate rollback of deployment pointers from rollback of data/index/schema
  changes;
- design bounded GPU smoke tests after CPU/static gates pass.

## What you will build

The local pipeline creates:

1. an immutable release validation result;
2. a rendered private Kubernetes Deployment/Service;
3. atomic `staging.json` and `production.json` environment pointers;
4. an append-only `promotion-history.ndjson`;
5. a loopback runtime exposing `/healthz`, `/release`, and
   `/v1/chat/completions`;
6. a behavioral smoke result that checks health, release identity, required
   concepts, and forbidden unsafe advice;
7. evidence that an invalid release is blocked before deployment;
8. evidence that a metadata-valid regression fails in staging and is rolled
   back without changing production.

The GitOps examples include a private digest-pinned workload with default-deny
networking and an explicit authenticated-gateway path, an Argo CD `Application`
template pinned to a source revision, and a read-only GitHub Actions validation
workflow. They are teaching files; no remote registry, cluster, Git provider,
or Argo CD instance is mutated by the required path.

## Files in this lesson

```text
48-cicd-gitops-reproducibility/
├── README.md
├── release.schema.json
├── gitops/
│   ├── argocd-application.yaml.tpl
│   └── deployment.yaml.tpl
├── pipeline/
│   └── validate-release.yml
├── releases/
│   ├── candidate-good.json
│   ├── candidate-invalid.json
│   └── candidate-regression.json
├── scripts/
│   ├── run-deliberate-failure.sh
│   ├── run-local-pipeline.sh
│   ├── run-smoke.sh
│   └── verify_pipeline.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── promote.py
    ├── render_release.py
    ├── smoke_check.py
    ├── smoke_service.py
    └── validate_release.py
```

Generated desired state, pointers, logs, and failure evidence live under
ignored `artifacts/`.

## Under the hood

### The release is a graph

The contract links:

```text
source commit -> image digest
base model revision <-> tokenizer revision
base model revision <-> adapter base revision
adapter bytes -> adapter digest
corpus/index version -> index digest
configuration -> configuration digest
quality/performance/security reports -> evidence digests
```

Each edge is a compatibility claim. An adapter trained against one base revision
can load against another and produce silent regressions or explicit shape
errors. A tokenizer change can alter role markers and token IDs without changing
model weights. A new index can change answers while the model image remains
identical.

The lesson requires every declared gate to be `pass` and bound by a digest.
Those fixture digests are synthetic teaching values; a real pipeline calculates
them from actual evidence.

### Immutability and reproducibility

An image digest identifies registry bytes. A source commit identifies a Git
tree/history point. A model Hub commit identifies one repository snapshot.
They do not automatically prove a hermetic or reproducible build. Package
repositories, base images, generated code, compilers, clocks, and external
downloads can still vary.

Record and pin all inputs, then compare independently rebuilt outputs when
reproducibility matters. Preserve provenance rather than claiming “same commit”
is sufficient.

### Desired state and runtime state

GitOps declares desired state in Git and a controller reconciles the cluster.
That makes change history reviewable and detects drift, but a committed manifest
does not prove:

- the controller synced it;
- the image pulled;
- the Pod became ready;
- the model/index loaded;
- runtime identity matches the intended contract;
- behavior clears gates.

The smoke service exposes `/release` so the verifier compares runtime release,
image, model revision, and index version with the promoted contract. In a real
service, expose safe non-secret build metadata through a protected operator
endpoint or metrics, not arbitrary filesystem/config dumps.

### Stages and promotion

Build once, promote the same immutable release:

```text
source -> build/attest -> CPU gates -> staging deploy
       -> runtime identity -> behavioral/quality/performance/security smoke
       -> approved promotion -> production
```

Rebuilding separately for production creates different bytes. Changing model,
adapter, index, or configuration between stages creates a different release and
must repeat gates.

### Compare-and-swap

`promote.py` requires the caller to state the current release it expects. If the
environment changed since review, promotion stops:

```text
expected current != observed current -> no write
```

This protects against overwriting an emergency rollback or another promotion.
The local implementation holds an exclusive state-directory lock while it
rechecks the expected pointer, writes a temporary file, flushes/fsyncs, and
atomically replaces the pointer. A production GitOps path uses a reviewed
commit/PR and controller state rather than this local file, but the concurrency
principle is the same.

### Health is not behavior

The regression fixture is healthy and immutable. It fails because its answer
omits readiness/selector/endpoints and recommends restarting the cluster and
exposing a load balancer.

Smoke should check the smallest high-value behaviors:

- process health and readiness;
- runtime release identity;
- model load and response schema;
- one deterministic correctness case;
- one critical safety/authorization case;
- retrieval/index identity if present;
- telemetry path.

It does not replace the full lesson-34 evaluation or lesson-45 load study.

### Rollback boundaries

Deployment rollback moves a pointer to known-good immutable artifacts. Data and
schema changes may not be backward compatible. An index built from deleted or
updated source data may need its own versioned rollback. A merged model cannot
“unmerge” at runtime unless the previous bytes remain available.

Define which components roll back together and how stateful changes are
forward/backward compatible. Retain the previous release long enough to recover,
subject to data deletion and vulnerability requirements.

### Canary and progressive delivery

A canary sends a bounded audience or traffic percentage to a candidate while a
stable release remains available. Promotion requires:

- comparable request mix;
- candidate/stable identity labels;
- quality/safety guardrails;
- latency/error/queue metrics;
- minimum sample/window;
- automatic and operator stop conditions;
- no cross-version state incompatibility.

Do not route restricted users to a canary before authentication and tenant
authorization are verified.

## Prerequisites and preflight

Run locally:

```bash
cd lessons/phase-07-production/48-cicd-gitops-reproducibility
python3 --version
curl --version | head -n 1
python3 -m json.tool releases/candidate-good.json >/dev/null
python3 -m json.tool release.schema.json >/dev/null
```

Confirm the smoke port is unused:

```bash
export OMS_SMOKE_PORT=8048
if curl -fs "http://127.0.0.1:$OMS_SMOKE_PORT/healthz" >/dev/null 2>&1; then
  echo "Choose another OMS_SMOKE_PORT"
  exit 1
fi
```

Inspect the good contract:

```bash
python3 src/validate_release.py --release releases/candidate-good.json
```

For optional GitOps, verify `kubectl`, the GitOps controller, repository access,
namespace, workload identity, registry/model permissions, and rollback owner.
Do not give a learning pipeline production write credentials.

## Cost and safety

The required lab binds only to loopback and uses no cloud service.

The CI workflow has `contents: read`; it does not publish or deploy. Real
pipelines should separate untrusted pull-request validation from trusted
signing/publishing and environment promotion. Never expose secrets to code from
an untrusted fork.

GPU smoke runs only after static, schema, policy, and CPU tests pass. Bound
replicas, requests, maximum tokens, and duration. Use a private ClusterIP and
port-forward or an authenticated private gateway. Verify anonymous denial before
attaching restricted artifacts.

Do not use mutable tags, branches such as `main`, or `latest` for promoted
artifacts. Do not put registry credentials, Hub tokens, account IDs, cluster
endpoints, or private repository URLs into the release JSON.

## Predict before running

Create `artifacts/predictions.md`:

1. Will the invalid candidate reach staging?
2. Will the regression candidate pass metadata validation?
3. Which gate catches the regression?
4. Should production change after failed staging smoke?
5. Why must adapter base revision equal release model revision?
6. Why can a source commit still produce nonreproducible image bytes?
7. What does compare-and-swap protect?
8. Does GitOps sync prove model behavior?
9. Which state changes might make rollback unsafe?
10. What should happen if runtime `/release` differs from desired state?

Preserve predictions.

## Lab outline

1. Inspect the complete immutable release contract.
2. Validate and render the known-good fixture.
3. Promote it atomically to staging.
4. run loopback health, identity, and behavioral smoke.
5. Promote the same contract to production.
6. Reject a structurally invalid release.
7. Stage a metadata-valid behavioral regression.
8. Block production and roll staging back.
9. Map the local steps to CI and GitOps.

## Step-by-step lab

### 1. Run the happy-path pipeline

```bash
chmod +x scripts/*.sh
./scripts/run-local-pipeline.sh
```

Expected shape:

```text
PASS: oms-2026-10-21.1 is immutable, compatible ...
rendered=.../rendered-staging.yaml
promoted environment=staging from=NONE to=oms-2026-10-21.1
PASS: ... behavioral smoke checks passed
promoted environment=production from=NONE to=oms-2026-10-21.1
PASS: staging and production point to ...
```

The invalid candidate failure is captured rather than printed as success.

### 2. Inspect release and rendered state

```bash
python3 -m json.tool artifacts/environments/staging.json
python3 -m json.tool artifacts/environments/production.json
sed -n '1,240p' artifacts/rendered-staging.yaml
```

Verify the rendered image matches the release digest and no template marker
remains:

```bash
grep -F '@sha256:' artifacts/rendered-staging.yaml
test -z "$(grep -E '__[A-Z_]+__' artifacts/rendered-staging.yaml || true)"
```

### 3. Inspect promotion history

```bash
cat artifacts/environments/promotion-history.ndjson
```

Each record has environment, prior release, new release, and timestamp. It is a
local teaching log, not a tamper-proof audit system.

### 4. Read the invalid-release evidence

```bash
cat artifacts/expected-invalid-release.txt
```

Map each failure to a release graph edge. Notice that one candidate can fail
many controls. Fixing the image digest does not repair model/tokenizer mismatch
or failed quality.

### 5. Run the regression and rollback

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-smoke-failure.txt
cat artifacts/environments/promotion-history.ndjson
```

Expected:

```text
PASS: oms-2026-10-21.2-regression is immutable, compatible ...
... regression was contained in staging and staging rolled back
```

The smoke log must report missing concepts and forbidden advice. Verify
production never left `oms-2026-10-21.1`.

### 6. Demonstrate drift protection

Try an incorrect expected current:

```bash
set +e
python3 src/promote.py \
  --candidate releases/candidate-good.json \
  --environment production \
  --state-dir artifacts/environments \
  --expected-current something-else
status=$?
set -e
test "$status" -ne 0
```

No production file should change.

### 7. Map to real CI/GitOps

Inspect:

```bash
sed -n '1,240p' pipeline/validate-release.yml
sed -n '1,260p' gitops/argocd-application.yaml.tpl
```

A real pipeline adds:

- dependency/secret/license/vulnerability scans;
- container build, SBOM, signature, and provenance;
- model/adapter/index upload and digest resolution;
- policy/schema/render validation;
- full quality/retrieval/performance/security evidence;
- ephemeral private environment;
- approval and audited Git promotion;
- post-sync identity and behavior verification.

Do not put deployment credentials in pull-request jobs.

## Deliberate failure

The required failure is a metadata-valid regression:

```bash
./scripts/run-deliberate-failure.sh
```

The staged runtime is healthy and reports the expected candidate release, but
behavior fails. The script verifies production remains known-good, then rolls
staging back with compare-and-swap.

Additional safe failures:

- change adapter base revision and confirm validation fails;
- change runtime release ID and confirm smoke fails;
- add a mutable image tag and confirm render/validation fails;
- simulate another promotion between review and write and confirm CAS fails;
- remove one evidence gate and confirm release validation fails.

Never test rollback first in production.

## Verification

Run:

```bash
./scripts/run-local-pipeline.sh
./scripts/run-deliberate-failure.sh
python3 scripts/verify_pipeline.py \
  --state-dir artifacts/environments \
  --expected-release oms-2026-10-21.1
```

Verify production history never contains the regression:

```bash
python3 - <<'PY'
import json
from pathlib import Path

rows = [
    json.loads(line)
    for line in Path(
        "artifacts/environments/promotion-history.ndjson"
    ).read_text().splitlines()
]
bad = [
    row for row in rows
    if row["environment"] == "production"
    and row["to"] == "oms-2026-10-21.2-regression"
]
assert not bad
print("PASS: failed candidate never reached production")
PY
```

For a real deployment, verification includes desired Git revision, controller
sync/health, runtime release endpoint, image digest from Pod status, model/index
identity, quality/safety smoke, telemetry, anonymous denial, and cleanup of the
ephemeral environment.

## Troubleshooting

If the smoke port is occupied, choose another `OMS_SMOKE_PORT`; do not kill an
unidentified service.

If a valid release fails validation, inspect exact hex lengths, case, adapter
base revision, tokenizer revision, index version, and required gates.

If the smoke service starts but identity differs, stop promotion. Determine
whether desired state, controller cache, image pull policy, environment config,
or runtime metadata is stale.

If CAS fails, read current state and promotion history. Do not retry with a new
expected value until you understand the intervening change.

If Argo CD reports Synced but Pods fail, inspect health, events, image/model
access, scheduling, probes, and runtime identity. Synced means desired objects
match, not application success.

If rollback restores the image but behavior remains changed, check model,
adapter, index, config, caches, and stateful migrations. Roll back the whole
release graph.

If a GPU ephemeral environment cannot start, preserve failure evidence and
clean up. Do not bypass CPU/security gates or expand quotas automatically.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── rendered-staging.yaml
├── environments/
│   ├── staging.json
│   ├── production.json
│   └── promotion-history.ndjson
├── smoke-server.log
├── expected-invalid-release.txt
├── expected-smoke-failure.txt
├── ci-run.json
├── gitops-sync.json
├── runtime-release.json
├── rollback-timeline.md
├── cleanup-inventory.json
└── report.md
```

The report must connect source revision to every artifact/evidence digest,
describe stage/prod identity, explain failed gates, show rollback, identify
stateful compatibility, state cost, and prove cleanup.

## Exercises

1. Calculate fixture evidence digests from real lesson reports rather than
   placeholder teaching values.
2. Add JSON Schema validation using a pinned validator, then retain semantic
   compatibility checks.
3. Generate an SBOM and signed provenance for a built image.
4. Add a policy that rejects public Services and mutable images.
5. Add a canary pointer and require candidate/stable labeled metrics.
6. Simulate concurrent promotion and emergency rollback.
7. Add index schema migration compatibility and rollback.
8. Compare runtime Pod image ID with the release digest.
9. Add anonymous and unauthorized denial smoke tests.
10. Build an ephemeral namespace workflow with a strict GPU-minute cap.
11. Add a reproducible-build comparison from two isolated builders.
12. Turn environment promotion into a reviewed Git commit and verify controller
    reconciliation without giving PR jobs write access.

## Completion gate

You are done when:

- the good pipeline passes from validation through production pointer;
- the invalid candidate is blocked before staging;
- the valid regression is caught by behavior;
- production never points to the regression;
- staging rollback is recorded and verified;
- CAS blocks unexpected drift;
- rendered Kubernetes state is private and digest-pinned;
- runtime identity is checked;
- a real release graph includes actual evidence digests, not fixture values;
- optional GPU smoke is bounded and cleaned up;
- another operator can identify and restore the previous complete release.

## Cleanup

Stop any leftover loopback service by locating only this lesson's process, then:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

For an ephemeral cluster environment, stop traffic, delete the GitOps
`Application` only if that is the approved ownership path, wait for managed
objects to disappear, verify volumes/load balancers are removed, restore GPU
node capacity, revoke temporary credentials, and remove unretained registry or
artifact versions.

Retain release/provenance/history required for audit and rollback according to
policy; cleanup does not mean destroying required evidence.

## Primary references

Sources were reviewed on 2026-10-21:

- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [Argo CD declarative setup](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes image digests](https://kubernetes.io/docs/concepts/containers/images/#image-names)
- [SLSA provenance](https://slsa.dev/spec/v1.2/provenance)
- [Sigstore documentation](https://docs.sigstore.dev/)
- [OCI image specification](https://github.com/opencontainers/image-spec)
- [OpenGitOps principles](https://opengitops.dev/)

The loopback pipeline, smoke, promotion, failure, and rollback paths are
author-validated. The release values are explicit teaching fixtures; no image
was built/pushed, no remote CI or GitOps controller ran, and no Kubernetes/GPU
deployment was performed for this draft.
