# 44 — Capstone: deploy the knowledge system

**Status:** draft
**Time:** 2–3 days
**Compute:** `local-cpu`; optional Kubernetes CPU deployment and internal GPU model endpoints
**Prerequisites:** 39–43
**Last reviewed:** 2026-10-21

## Why this matters

A useful RAG prototype is not merely a notebook that returns a plausible
paragraph. It is a versioned system with an ingestion contract, retrieval
evidence, grounded answers, identity boundaries, health signals, deployment
artifacts, update behavior, rollback, and an experiment that explains when the
added machinery helps.

This capstone integrates lessons 41–43 into a real HTTP service and preserves
lesson 40’s decision logic. It exposes health, readiness, Prometheus text
metrics, and a query endpoint. At startup it validates and indexes one immutable
corpus snapshot. A caller principal is mapped to a tenant before retrieval; the
request body cannot choose its own tenant. The answer preserves index hash,
candidate IDs, bounded context, citations, and source spans.

The local path needs only Python’s standard library and is executed by the
repository checks. The container and Kubernetes path is practical but cannot
be claimed as live-tested without your Docker daemon, registry, cluster,
network-policy implementation, and namespace. It uses a digest-enforcing build
and renderer, non-root/read-only execution, a ClusterIP Service, default-deny
network policy, probes, and resource bounds.

The capstone also records a four-way comparison:

```text
base | tuned | RAG | tuned + RAG
```

The mandatory CPU variants are explicit contract proxies. “Tuned” means a
deterministic strict-JSON behavior adapter, not a trained checkpoint. Every
record says so. This validates the study harness without fabricating model
results. After lesson 39 produces a reviewed adapter and engine endpoint, an
optional recorder can replace the base/tuned proxies with real internal model
responses. Only those measured runs can support a model-quality conclusion.

Finally, the lab builds corpus v1, corpus v2, and v1 again. It proves that a
source update changes the answer and chunk version, while rollback restores the
original source hash, manifest, answer, and citation.

## Learning outcomes

By the end, you can:

- operate a local knowledge API with health, readiness, query, and metrics
  endpoints;
- derive tenant scope from a principal mapping rather than caller-provided
  document metadata;
- preserve the active source hash in readiness, metrics, and every response;
- explain which work belongs to ingestion, retrieval, grounding, and serving;
- compare base, tuned, RAG, and tuned-plus-RAG capability contracts using fixed
  inputs and recorded outputs;
- distinguish a deterministic training proxy from a real fine-tuned model;
- update and roll back a corpus while proving behavior and lineage;
- build a container only from a digest-pinned base image;
- deploy only a digest-pinned application image;
- render a Kubernetes Deployment, ConfigMap, ClusterIP Service, and
  NetworkPolicies;
- configure non-root, read-only, no-privilege, no-service-account-token pods;
- use liveness for process health and readiness for index availability;
- expose low-cardinality metrics without logging questions or document text;
- describe the identity, TLS, policy, storage, and observability work still
  needed before production.

## What you will build

The integrated architecture is:

```text
                         offline / startup
corpus snapshot -> validate -> chunk -> embed -> index + manifest
                                            |
                                            v
caller -> private ClusterIP -> principal adapter -> tenant entitlement
                                            |
                                            v
                              sparse+dense+RRF+rerank
                                            |
                                            v
                          injection scan + context budget
                                            |
                                            v
                          extractive fallback / optional model
                                            |
                                            v
                         citation and source-span validation
                                            |
                 +--------------------------+------------------+
                 |                          |                  |
               answer                    metrics           evidence
```

The local API has:

- `GET /healthz`: process is serving HTTP;
- `GET /readyz`: active index loaded, with source SHA-256;
- `GET /metrics`: request, abstention, error, and index-info metrics;
- `POST /v1/query`: exactly `{"question":"..."}` plus the demonstration
  `X-Course-Principal` header.

There is deliberately no public Ingress, LoadBalancer, corpus mutation
endpoint, arbitrary URL fetcher, or model tool execution.

The study runner records three questions across four variants. It then performs
the corpus update probe:

```text
v1: weekday 08:00–18:00 support
v2: twenty-four hours a day, seven days a week
rollback: original weekday answer and original hashes
```

## Files in this lesson

```text
44-capstone-knowledge-system/
├── README.md
├── configs/
│   ├── identities.json
│   ├── optional-gpu-variants.example.json
│   └── study-contract.json
├── container/
│   └── Dockerfile
├── data/
│   └── study-questions.json
├── k8s/
│   └── knowledge-service.yaml.tmpl
├── results.schema.json
├── scripts/
│   ├── build-image.sh
│   ├── cleanup.sh
│   ├── deploy.sh
│   ├── render-k8s.sh
│   ├── rollback-corpus.sh
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   ├── run-local-e2e.sh
│   ├── run-study.sh
│   ├── test-k8s.sh
│   ├── update-corpus.sh
│   └── verify.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── optional_gpu_study.py
    ├── render_k8s.py
    ├── service.py
    ├── study.py
    └── test_api.py
```

All generated indexes, responses, logs, and rendered manifests are ignored
under `artifacts/`.

## Under the hood

### Startup and readiness

`KnowledgeApplication` resolves the configured corpus beneath lesson 41,
validates it, builds the deterministic index into a writable temporary
directory, loads the reviewed retrieval and grounding configs, then marks
itself ready. The HTTP server does not begin until construction succeeds.

Liveness and readiness answer different questions:

- liveness asks whether the process can continue serving and should be
  restarted if it cannot;
- readiness asks whether this instance should receive query traffic, including
  whether its requested index is available.

This tiny service builds synchronously. A large system may download or attach
an immutable prebuilt index, warm caches, verify a manifest signature, and hold
readiness false until all gates pass. Do not use liveness to kill a pod merely
because a slow model/index warmup is still progressing.

### Identity before tenant scope

The request body accepts only `question`. It rejects a caller-supplied
`tenant_id`, even if a Beta principal tries to set it to Alpha. The
`X-Course-Principal` header maps through `identities.json`:

```text
learner-alpha -> alpha
learner-beta  -> beta
```

This is a teaching adapter, not authentication. Any local caller can forge the
header. In production, replace it with verified workload/user identity such as
an authenticated gateway, service mesh identity, cloud IAM integration, or
OIDC claims. Keep the mapping and policy decision server-side. The model never
chooses authorization.

Unknown principals receive `403`. Bodies with extra fields receive `400`.
Question size and body size are bounded. Responses set `Cache-Control:
no-store`.

### Query evidence

Every successful response records:

- generated request ID;
- derived principal and tenant;
- source file and SHA-256;
- retrieval method, candidates, and component timing;
- blocked chunks and bounded context;
- answer/abstention, claims, citations, and source spans;
- explicit deterministic-generator identity.

The access logger records method, path, status, client address, and timestamp.
It does not log question or document text. A production trace should use a
request ID and safe aggregate dimensions; avoid tenant, user, prompt, or chunk
IDs as unbounded metrics labels.

### Metrics

The service exposes Prometheus text:

```text
knowledge_requests_total
knowledge_abstentions_total
knowledge_errors_total
knowledge_index_info{source_sha256="..."} 1
```

The source hash label has low cardinality only if deployments activate a small,
controlled number of versions. Do not label every request with question,
principal, chunk, or arbitrary model output. Counters are process-local and
reset on restart; a scraper stores their time series.

The course handler uses a lock because `ThreadingHTTPServer` processes requests
concurrently. The Python implementation is an educational serving boundary,
not a high-throughput engine. Benchmark it before choosing worker counts,
limits, or autoscaling signals.

### Four-way study contract

The study fixes:

- source snapshot and question fixture;
- retrieval and grounding configuration;
- strict JSON fields;
- citation and abstention expectations;
- the implementation class of every variant.

It separates two dimensions:

| Variant | Knowledge source | Behavior format |
|---|---|---|
| base | none | plain |
| tuned | none | strict JSON |
| RAG | retrieval | plain |
| tuned + RAG | retrieval | strict JSON |

In the CPU harness, base and tuned variants abstain because no evidence is
supplied. The tuned proxy still demonstrates strict JSON behavior. RAG answers
with cited evidence. Tuned-plus-RAG wraps the same grounded evidence in the
strict JSON contract.

This does not prove that fine-tuning will achieve the format, that a base model
would abstain, or that RAG improves a particular LLM. Those require real model
and adapter revisions, identical prompts/decoding, repeated runs, quality
judges, latency, GPU telemetry, and cost evidence. The interpretation warning
is stored inside the contract, study output, and verifier.

### Update and rollback

Corpus v2 changes `alpha-support-guide` from version `1.0.0` to `2.0.0`. The
study builds separate immutable index directories and asks the same question.
It requires:

```text
v1 source hash != v2 source hash
v1 answer != v2 answer
v1 answer == rollback answer
v1 citations == rollback citations
v1 source hash == rollback source hash
v1 manifest == rollback manifest
```

The Kubernetes scripts use a mutable ConfigMap plus a controlled rollout
restart because that mechanism is easy to inspect. For stronger production
provenance, create immutable versioned ConfigMaps/index resources, update a
GitOps reference, verify readiness, shift traffic, and retain the previous
version for rollback.

There is no online ingestion endpoint. Corpus updates are deployment changes,
not unauthenticated HTTP mutations.

### Digest-enforcing container workflow

The Dockerfile has no default base:

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
```

`build-image.sh` rejects anything except `name@sha256:<64 lowercase hex>`.
After building and pushing, `render_k8s.py` separately rejects an application
tag and accepts only `repository@sha256:<digest>`. These two checks prevent a
mutable tag from silently changing either layer between review and deployment.

Digest pinning provides immutability, not trust. Also scan the image, produce
an SBOM, sign provenance, enforce admission policy, patch known
vulnerabilities, and retain the source-to-image relationship.

The container copies only required source/config/corpus files, runs as numeric
UID/GID `65532`, writes the index under `/tmp`, and exposes port 8080. It has no
shell startup wrapper or embedded credential.

### Kubernetes controls

The rendered manifest contains:

- ConfigMap selecting corpus v1;
- one-replica Deployment with rolling updates;
- non-root pod and container security contexts;
- `RuntimeDefault` seccomp, dropped capabilities, no privilege escalation;
- read-only root filesystem and bounded `emptyDir` for `/tmp`;
- disabled service-account token;
- CPU/memory requests and limits;
- liveness/readiness probes;
- ClusterIP Service only;
- default-deny ingress and egress;
- ingress allowed only from same-namespace pods labeled
  `course.open-model.dev/knowledge-client=true`.

The CPU fallback needs no network egress. An optional GPU model endpoint will
not work until you add a narrow egress rule, service authentication, and
approved encrypted transport. This fail-closed default is intentional.

A NetworkPolicy only works when the cluster networking implementation enforces
it. `kubectl port-forward` tests application behavior through the Kubernetes
control path; it does not prove pod-to-pod network policy. Test allowed and
denied pods separately.

## Prerequisites and preflight

For the required local path:

```bash
cd lessons/phase-06-rag/44-capstone-knowledge-system
python3 --version
python3 -m json.tool configs/study-contract.json >/dev/null
python3 -m json.tool configs/identities.json >/dev/null
python3 -m json.tool data/study-questions.json >/dev/null
```

For containers/Kubernetes, also check:

```bash
printf 'Enter the existing lab namespace: '
read -r COURSE_NAMESPACE
export COURSE_NAMESPACE
docker version
kubectl version --client
kubectl config current-context
kubectl auth can-i create deployments -n "$COURSE_NAMESPACE"
kubectl auth can-i create networkpolicies.networking.k8s.io \
  -n "$COURSE_NAMESPACE"
```

Set `COURSE_NAMESPACE` only to a pre-created lab namespace. Read your current
context and account before mutation. Confirm NetworkPolicy enforcement with
your cluster/CNI documentation.

## Cost and safety

The verified CPU path uses loopback, a tiny synthetic corpus, and temporary
files. It creates no cloud resource.

Docker builds can download layers and consume disk. Registry storage and
egress may cost money. Kubernetes pods consume requested CPU/memory until
deleted. Optional GPU endpoints can be materially expensive; scale them to zero
after the study and record instance, accelerator, region, duration, and
utilization.

The Kubernetes service is internal, but “private network” is not
authentication. Do not deploy real data behind the course principal header.
Add verified identity, authorization, TLS, secret management, audit controls,
retention, backup, deletion, and threat review first.

Do not put registry credentials, model tokens, cloud keys, or private corpus
content in this repository. Use your platform’s credential provider. The
optional endpoint recorder sends question text to configured services only
after an explicit `--acknowledge-data-transfer`; it also requires HTTPS, a
reviewed CA bundle, and an engine- or gateway-native bearer credential supplied
through environment variables.

## Predict before running

Write `artifacts/predictions.md`:

1. Which variants should satisfy strict JSON format?
2. Which should answer current corpus facts?
3. Can a tuned model without retrieval cite a source it never received?
4. Which identifiers must change from corpus v1 to v2?
5. What must be identical after rollback?
6. Why does readiness include the source hash?
7. Why are both base and application image digests required?
8. Does ClusterIP plus NetworkPolicy replace authentication?
9. Will `kubectl port-forward` prove NetworkPolicy enforcement?

## Lab outline

1. Start the service on loopback and wait for readiness.
2. Test health, readiness, authorized query, metrics, unknown identity, and
   tenant-smuggling rejection.
3. Run the fixed four-variant CPU contract study.
4. Build v1, v2, and rollback indexes and verify answer lineage.
5. Reject mutable container/deployment image references.
6. Review and render the Kubernetes manifest with an immutable digest.
7. Optionally build, push, deploy, and test in a private namespace.
8. Update corpus, verify the answer/hash, and roll back.
9. Optionally substitute real internal base/tuned GPU endpoints and repeat the
   study.

## Step-by-step lab

### 1. Run the complete local capstone

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected shape:

```text
PASS: health/readiness/query/metrics succeeded; unknown identity and tenant smuggling were rejected
recorded four variants across 3 questions
update changed answer= True rollback exact= True
PASS: local private API, four-way contract study, corpus update, and exact rollback were verified
```

The runner starts on `127.0.0.1:18080`, tests it, and stops it with a shell
trap. Override `COURSE_PORT` if that port is occupied.

### 2. Inspect HTTP evidence

```bash
python3 -m json.tool artifacts/local-api-results.json | sed -n '1,220p'
sed -n '1,120p' artifacts/service.log
```

Confirm:

- body contains only `question`;
- `learner-alpha` becomes tenant `alpha`;
- the source hash appears in readiness and the query;
- the claim cites a versioned chunk;
- unknown principal is forbidden;
- a body attempting to set tenant is rejected;
- logs omit the question.

### 3. Inspect the four-way study

```bash
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("artifacts/study-results.json").read_text())
print(r["interpretation"])
for name, result in r["variants"].items():
    print(name, result)
PY
```

Then inspect actual inputs and serialized outputs:

```bash
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("artifacts/study-results.json").read_text())
for record in r["records"]:
    if record["input"]["question_id"] == "token-expiry":
        print(record["variant"], record["implementation_class"])
        print(record["output"]["serialized"])
PY
```

Do not shorten implementation labels in a report. They prevent proxy evidence
from being mistaken for model evidence.

### 4. Inspect update and rollback

```bash
python3 - <<'PY'
import json
from pathlib import Path
u = json.loads(Path("artifacts/study-results.json").read_text())["update_rollback"]
for stage in ("v1", "v2", "rollback"):
    print(stage, u[stage]["source_sha256"], u[stage]["answer"])
print("changed:", u["changed_on_update"])
print("rollback exact:", u["rollback_exact"])
print("citations exact:", u["rollback_citations_exact"])
print("manifest exact:", u["v1_manifest_matches_rollback"])
PY
```

The v2 citation must use document version `2.0.0`; v1 and rollback use
`1.0.0`.

### 5. Resolve and build immutable images

Inspect a candidate base:

```bash
docker buildx imagetools inspect python:3.12-slim
```

After reviewing platform and digest, set an immutable reference and a registry
tag:

```bash
printf 'Paste the reviewed base image name@sha256 digest: '
read -r BASE_IMAGE_REF
printf 'Enter the registry/repository:tag you are allowed to push: '
read -r IMAGE_TAG
export BASE_IMAGE_REF IMAGE_TAG
./scripts/build-image.sh
docker push "$IMAGE_TAG"
docker buildx imagetools inspect "$IMAGE_TAG"
```

Copy the pushed manifest digest, not a local image ID:

```bash
printf 'Paste the pushed application repository@sha256 digest: '
read -r IMAGE_REF
export IMAGE_REF
```

The scripts reject missing, mutable, or malformed digest values.

### 6. Render and review Kubernetes

```bash
printf 'Enter the existing lab namespace: '
read -r COURSE_NAMESPACE
export COURSE_NAMESPACE
./scripts/render-k8s.sh
kubectl apply --dry-run=client \
  -f artifacts/rendered-knowledge-service.yaml
kubectl diff -f artifacts/rendered-knowledge-service.yaml || true
```

Review all objects before applying. Confirm no `Ingress`, `LoadBalancer`, host
path, privileged container, mutable image, or Secret value appears.

### 7. Deploy and test

```bash
./scripts/deploy.sh
kubectl -n "$COURSE_NAMESPACE" get pods,service,networkpolicy
./scripts/test-k8s.sh
```

`test-k8s.sh` records API evidence through a temporary port-forward. To verify
network policy, create one disposable same-namespace client pod with the
allowed label and another without it; the labeled request should connect and
the unlabeled request should time out. Use a reviewed image and delete both
test pods immediately.

### 8. Update and roll back on Kubernetes

Record the current readiness hash and support answer, then:

```bash
./scripts/update-corpus.sh
./scripts/test-k8s.sh
cp artifacts/k8s-api-results.json artifacts/k8s-api-results-v2.json
./scripts/rollback-corpus.sh
./scripts/test-k8s.sh
cp artifacts/k8s-api-results.json artifacts/k8s-api-results-rollback.json
```

The included API test asks token expiry rather than support hours. Add the
update-probe request from `data/study-questions.json` or use the local study
artifact as your exact expected contract. Record ready hashes at all stages.

### 9. Optional real GPU endpoints

Lesson 39 should provide exact base model and tuned adapter revisions. Copy the
example config under ignored artifacts and replace its endpoint/model labels
with reviewed in-cluster services and exact revisions. Provision the serving
engine or gateway’s native bearer credential and the reviewed cluster CA bundle
through your secret provider, expose them only to this process as
`COURSE_MODEL_BEARER_TOKEN` and `COURSE_MODEL_CA_BUNDLE`, and add a narrow
egress policy. Then run:

```bash
python3 src/optional_gpu_study.py \
  --config artifacts/gpu-variants.json \
  --questions data/study-questions.json \
  --output artifacts/gpu-variant-responses.json \
  --work-dir artifacts/gpu-study-index \
  --acknowledge-data-transfer
```

This recorder calls the base endpoint for base/RAG and the tuned endpoint for
tuned/tuned-plus-RAG. It builds the same lesson-43 context for both RAG paths
and records every prompt and raw response. It refuses plaintext HTTP, hosts
outside the reviewed cluster DNS suffix, missing credentials, or a missing CA
bundle, and it does not follow redirects that could move data or credentials
to another host. Before acceptance, validate claims and citations and record
engine, model/adapter digest, decoding, latency percentiles, GPU memory,
utilization, and cost. The repository’s CPU verification did not call these
endpoints.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
sed -n '1,80p' artifacts/failures/mutable-base.txt
sed -n '1,80p' artifacts/failures/mutable-image.txt
```

The build wrapper rejects `python:3.12-slim` because it is a mutable tag. The
renderer rejects `knowledge-service:mutable` for the same reason. Neither
Docker nor Kubernetes is invoked before rejection. A third case attempts to
make the service index a path outside lesson 41’s controlled corpus directory;
startup rejects it before reading the target. A fourth tries to use the
optional model recorder without its native bearer credential or reviewed CA
bundle; it fails before indexing or opening a connection.

Expected:

```text
PASS: mutable images, escaped corpus paths, and unauthenticated model calls were rejected before external mutation
```

Recovery requires resolving, reviewing, and supplying registry digests. Keep
corpus paths inside the reviewed source directory. Provision endpoint
credentials and CA material through the platform’s secret provider; do not
weaken any guard.

## Verification

Local verification:

```bash
python3 scripts/verify.py
python3 -m json.tool artifacts/results.json >/dev/null
```

Rendered-manifest verification with a syntactically valid non-deployable
example:

```bash
IMAGE_REF="example.invalid/knowledge-service@sha256:$(printf 'a%.0s' {1..64})" \
COURSE_NAMESPACE=rag-course \
./scripts/render-k8s.sh
kubectl apply --dry-run=client \
  -f artifacts/rendered-knowledge-service.yaml
```

Do not deploy the `example.invalid` image. Some `kubectl` versions still use
API discovery during client dry-run, so this command may require a reachable
cluster; an offline run should use a reviewed Kubernetes schema validator.
A complete live evidence pack also needs rollout status, pod security fields,
Service type, NetworkPolicy behavior, probe results, actual image ID,
update/rollback hashes, and cleanup.

## Troubleshooting

If local readiness never succeeds, inspect `artifacts/service.log`. Common
causes are an occupied port, invalid corpus, missing sibling lesson files, or an
unwritable index directory.

If an authorized query returns `403`, verify the exact
`X-Course-Principal` value and `identities.json`. Do not add tenant to the body.

If a read-only container fails at startup, confirm `COURSE_INDEX_DIR` points
under the writable `/tmp` volume and the pod runs with the expected fsGroup.

If a pod is ready but clients cannot connect, inspect Service selectors,
Endpoints, port names, and NetworkPolicy. An unlabeled client is expected to
fail. Confirm your CNI enforces policy.

If the pod cannot call an optional model endpoint, default-deny egress is
working. Add only the destination/port required, then authenticate the model
request. Avoid broad Internet egress.

If the ConfigMap changes but answers do not, a running process does not
automatically rebuild an env-configured index. The update script performs a
rollout restart. Check new pod readiness source hash before testing.

If rollback answer differs while source hash matches, compare configuration,
code image digest, and index manifest. A rollback must cover all relevant
artifacts, not just corpus.

## Evidence to collect

Retain:

- predictions and architecture diagram;
- `local-api-results.json`, safe service logs, and metrics excerpt;
- study contract/question hashes and every recorded variant output;
- explicit proxy interpretation and, later, actual model/adapter identities;
- v1/v2/rollback source hashes, manifests, answers, citations, and rollout
  revisions;
- base and application image digests, Dockerfile hash, scan, SBOM, signature,
  and provenance if built;
- rendered manifest, client-side dry run, diff, rollout status, pod image IDs,
  probes, resource use, and policy tests if deployed;
- deliberate-failure logs;
- final `results.json`;
- cost and cleanup evidence for CPU, registry, cluster, and any GPU service.

## Exercises

1. Replace the demonstration identity map with a verified local reverse proxy
   and prove the body still cannot choose tenant.
2. Add a `/version` response binding code, configs, corpus, and image digest.
3. Prebuild the index as an immutable artifact and verify its signed manifest
   at startup.
4. Add a bounded request queue and measure overload behavior.
5. Export OpenTelemetry traces without recording question or chunk text.
6. Create versioned immutable ConfigMaps instead of patching one object.
7. Add an allowed labeled client and denied unlabeled client NetworkPolicy
   test script for your cluster.
8. Deploy a reviewed base model and lesson-39 adapter, then replace proxies
   with real results under the same study contract.
9. Split retrieval and generation into separate Deployments and identify new
   authentication, network, scaling, and failure boundaries.
10. Add canary rollout and automatic rollback based on retrieval, answer,
    security, and latency gates.

## Completion gate

You are finished when:

- local health, readiness, query, and metrics pass;
- unknown identity and tenant-smuggling input are rejected;
- the active source hash appears in readiness, metrics, and responses;
- the four variants run on identical inputs with their true implementation
  classes recorded;
- proxy results are not described as fine-tuned model measurements;
- v2 changes answer/source/version and rollback exactly restores v1 evidence;
- mutable base and deployment images fail before external mutation;
- the rendered workload is non-root, read-only, bounded, ClusterIP-only, and
  default-deny;
- optional live results include exact image/model/adapter/config/corpus
  identities and measured evidence;
- all deployed resources and optional GPU capacity are cleaned up.

## Cleanup

Stop/delete only resources created for this lesson:

```bash
printf 'Enter the existing lab namespace used by this lesson: '
read -r COURSE_NAMESPACE
export COURSE_NAMESPACE
./scripts/cleanup.sh
kubectl -n "$COURSE_NAMESPACE" get \
  deployment,service,configmap,networkpolicy \
  -l app.kubernetes.io/part-of=open-model-course
```

The script retains the namespace. Delete pushed images according to registry
retention policy and scale optional GPU endpoints to zero.

Remove local ignored artifacts after preserving evidence:

```bash
pwd
rm -rf artifacts/
rm -rf ../41-ingestion-chunks-embeddings-indexes/artifacts/
rm -rf ../42-retrieval-hybrid-reranking/artifacts/
rm -rf ../43-grounded-generation-rag-evaluation-security/artifacts/
```

## Primary references

Reviewed 2026-10-21:

- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes liveness, readiness, and startup probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes security contexts](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes image digests](https://kubernetes.io/docs/concepts/containers/images/#image-names)
- [Docker image digests](https://docs.docker.com/dhi/core-concepts/digests/)
- [Prometheus exposition formats](https://prometheus.io/docs/instrumenting/exposition_formats/)
- [SLSA provenance specification](https://slsa.dev/spec/v1.0/provenance)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

These references define platform mechanisms and risk practices. Local artifacts
support only the CPU service and study. Docker, Kubernetes, registry, and GPU
claims require evidence from the learner’s actual environment.
