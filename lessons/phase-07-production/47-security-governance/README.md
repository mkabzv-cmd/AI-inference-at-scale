# 47 — Security and governance

**Status:** draft
**Time:** 8–14 hours
**Compute:** `local-cpu`; optional brief private-cluster verification
**GPU budget:** none required
**Prerequisites:** 43–46
**Last reviewed:** 2026-10-21

## Why this matters

An open-model platform is not only an HTTP server. It combines base weights,
tokenizers, container images, native libraries, datasets, adapters, indexes,
object storage, caches, Kubernetes identities, cloud APIs, user prompts,
retrieved documents, responses, logs, and telemetry. Each crosses a trust
boundary.

Several dangerous assumptions are common:

- “The model file is data, so loading it cannot execute anything.”
- “ClusterIP means authenticated.”
- “A NetworkPolicy is tenant authorization.”
- “A digest proves the artifact is trustworthy.”
- “A license field means legal review is complete.”
- “RAG documents are trusted because they came from our index.”
- “Deleting the Deployment deletes every copy of the data.”

This lesson replaces those assumptions with explicit assets, principals, data
flows, controls, and verification. The required lab builds a small provenance
bundle, binds three artifacts to SHA-256 hashes and declared licenses, verifies
an exact fail-closed file set, tampers with one artifact, and proves rejection.
It also statically checks a private restricted Kubernetes workload and rejects a
fixture containing a public load balancer, host networking, a privileged
container, and a mutable image tag.

The Kubernetes sample has no public route. Network segmentation is not presented
as user authentication. `AUTH-RELEASE-GATE.md` requires the deployment to remain
private until a platform-native identity and action-authorization gate has
proved anonymous and unauthorized denial.

## Learning outcomes

By the end, you can:

- enumerate model-platform assets and trust boundaries;
- draw identities and data flows across ingestion, training, registry,
  deployment, retrieval, serving, and telemetry;
- build a threat register with preconditions, impact, controls, verification,
  residual risk, and owner;
- distinguish authentication, authorization, network segmentation, and
  encryption;
- keep local development on loopback and Kubernetes services private by
  default;
- explain why restricted content must be attached only after anonymous denial
  is verified;
- use workload identity instead of static cloud credentials;
- apply restricted Pod security settings and default-deny networking;
- pin images and model revisions and verify exact artifact hashes;
- explain what hashes, signatures, provenance, SBOMs, vulnerability scans,
  licenses, and evaluation each do—and do not—prove;
- prefer data-only artifact formats while recognizing parser and resource risks;
- test tampering, cross-tenant retrieval, prompt injection, overload, and
  incomplete deletion;
- assign residual risk and control ownership instead of declaring a system
  “secure.”

## What you will build

The CPU lab creates a local teaching bundle containing:

- a base-model card with an immutable model revision;
- a LoRA adapter configuration;
- a retrieval-index manifest;
- a generated provenance statement with role, source, license, byte size, and
  SHA-256 for every declared file.

The verifier fails if:

- a required artifact is missing or becomes a symlink;
- bytes or size differ;
- an undeclared file appears;
- a dangerous deserializing suffix such as `.pkl`, `.pt`, or `.bin` appears in
  this teaching bundle.

The Kubernetes contract includes:

- restricted Pod Security Admission namespace labels;
- non-root UID/GID and runtime-default seccomp;
- no privilege escalation and all Linux capabilities dropped;
- read-only root filesystem plus bounded `emptyDir`;
- no mounted Kubernetes API token;
- digest-pinned image;
- private `ClusterIP`;
- ingress default deny with one explicit gateway path;
- egress default deny with DNS only;
- a fail-closed ValidatingAdmissionPolicy example.

You will create your own threat model and authentication release checklist, then
run two deliberate failures: artifact tampering and an unsafe workload.

## Files in this lesson

```text
47-security-governance/
├── README.md
├── AUTH-RELEASE-GATE.md
├── THREAT-MODEL-TEMPLATE.md
├── configs/
│   └── bundle.json
├── fixtures/
│   ├── adapter-config.json
│   ├── index-manifest.json
│   └── model-card.json
├── k8s/
│   ├── broken-workload.yaml
│   └── restricted-workload.yaml
├── policies/
│   └── validating-admission-policy.yaml
├── results.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   └── verify-k8s-security.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── build_provenance.py
    └── verify_provenance.py
```

Generated bundle and failure logs go under ignored `artifacts/`.

## Under the hood

### Assets, principals, and trust boundaries

An asset is something whose confidentiality, integrity, availability, or
authorized use matters. A principal is an authenticated workload, user, or
service. A trust boundary is where identity, ownership, privilege, or data
classification changes.

Example:

```text
author -> source repository -> CI builder -> registry
                                      |
                                      v
data owner -> dataset -> trainer -> adapter/object store
                                      |
caller -> identity gateway -> model API -> retrieval index -> documents
                                      |
                                      v
                               logs / traces / metrics
```

Ask at every arrow:

- Who sends this?
- How is identity proved?
- Which action and tenant are authorized?
- Can content be modified or replayed?
- Is the parser safe for the format and size?
- Where is it logged, cached, backed up, and deleted?
- What evidence detects failure?

### Authentication is not authorization

Authentication establishes who the caller is. Authorization decides whether
that principal may perform this action on this tenant/resource. A signed
identity with no action-level policy is incomplete.

For AWS service callers, use an AWS-native mechanism such as SigV4/AWS IAM at a
supported private gateway and define least-privilege actions/resources. For
human users, use the organization's supported identity gateway. Do not invent a
shared bearer-token system for a tutorial.

If the real identity integration is unavailable, remain private and fail
closed. A middleware check that accepts any non-empty header verifies nothing.

### Verify denial before content

For restricted content, deployment order matters:

1. create the empty/private origin;
2. attach authentication and authorization;
3. make an anonymous request and require an identifiable 401/403 from the
   intended gate;
4. make an authenticated but unauthorized request and require denial;
5. verify one authorized action/tenant;
6. only then attach restricted model/data content;
7. repeat denial tests after policy changes.

A DNS error, timeout, or missing object does not prove the auth gate works. A
bare 403 may come from the wrong layer; inspect identifying response evidence.

### Network boundaries

`ClusterIP` prevents Kubernetes from provisioning a public load balancer. It
does not authenticate callers inside the network. NetworkPolicy restricts Pod
traffic only when the cluster's network implementation enforces it. Labels are
part of the policy trust model and must be controlled.

The sample starts with default deny. One ingress rule permits only a specifically
labeled authenticated gateway Pod in a named namespace. The model cannot fetch
arbitrary internet content; only DNS egress is allowed. A real design adds
explicit destinations such as a private artifact endpoint or retrieval service.
Avoid wide CIDRs and never expose datastores directly to the internet.

### Workload identity and secrets

The sample disables the Kubernetes service-account token because the process
does not need the API. If a workload needs AWS access, use the EKS-supported
workload identity mechanism with a scoped IAM role and SDK credential chain.
Do not bake keys into images, ConfigMaps, environment examples, or model
repositories.

Secrets can leak through shell history, Pod specs, logs, crash reports, debug
endpoints, traces, and CI artifacts. Prefer a platform secret provider, short
lifetime, rotation, audit, and minimal audience. A Kubernetes Secret is an API
object, not automatic end-to-end protection.

### Artifact integrity and provenance

SHA-256 answers whether bytes match a recorded digest. It does not establish who
created them, whether the source was reviewed, whether the build was isolated,
or whether the content is safe.

A stronger release chain may include:

- source revision and reviewed change;
- reproducible/hermetic build definition;
- software bill of materials (SBOM);
- vulnerability and license results;
- model/dataset card and immutable revisions;
- signed provenance/attestation;
- signature/identity verification policy;
- transparency log;
- runtime admission policy;
- evaluation and rollback.

These claims complement rather than replace one another.

### Model and checkpoint formats

General-purpose object deserialization can execute code or construct unexpected
objects. Prefer a data-only tensor format such as safetensors when supported,
use trusted parsers, verify digest/size/shape, and avoid remote custom code
unless it has been explicitly reviewed and pinned.

A data-only format still permits denial of service through huge allocations,
malformed metadata, parser vulnerabilities, or incompatible shapes. Load
untrusted artifacts in a constrained verification environment before
promotion.

### Data and RAG governance

Dataset and document permissions must survive normalization, chunking,
embedding, indexing, caching, and retrieval. Filter by authorized metadata
before untrusted text enters the model prompt. Test cross-tenant negative cases.

Retrieved documents can contain indirect prompt injection. Treat them as quoted
evidence, not instructions. Separate trusted system policy from untrusted
content, constrain tools, require citations, and test malicious documents.

Deletion must cover raw source copies, processed data, chunks, embeddings,
indexes, caches, checkpoints/adapters, logs, backups, and replicas. Record legal
retention conflicts and ownership.

### Kubernetes enforcement

The restricted manifest is defense in depth:

- namespace admission policy rejects nonconforming Pods;
- Pod/container security contexts reduce Linux privilege;
- immutable images reduce substitution;
- read-only filesystem reduces persistence;
- no API token reduces credential exposure;
- NetworkPolicy reduces reachability;
- resource limits bound some denial-of-service paths.

It does not provide model-level authorization, content safety, node isolation,
kernel security, or supply-chain trust by itself.

## Prerequisites and preflight

Run locally:

```bash
cd lessons/phase-07-production/47-security-governance
python3 --version
python3 -m json.tool configs/bundle.json >/dev/null
python3 -m json.tool fixtures/model-card.json >/dev/null
```

Read before execution:

```bash
sed -n '1,240p' AUTH-RELEASE-GATE.md
sed -n '1,260p' THREAT-MODEL-TEMPLATE.md
```

Search the lesson's safe deployment for exposure/privilege:

```bash
grep -nE 'LoadBalancer|hostNetwork|privileged|:latest|hostPath' \
  k8s/restricted-workload.yaml || true
```

For optional cluster checks:

```bash
kubectl config current-context
kubectl auth can-i create deployments -n oms-lesson-47
kubectl api-resources | grep ValidatingAdmissionPolicy
```

Do not apply an admission policy cluster-wide from a learning account without
understanding binding scope and recovery.

## Cost and safety

The required lab is offline and uses only tiny metadata fixtures.

The unsafe workload is a negative fixture. Never apply it. It contains a public
`LoadBalancer`, privileged execution, host networking, and mutable image tag.

The restricted workload uses an `example.invalid` digest and is for static
inspection. Replace it only with an approved private image digest. It contains
no real model or secret.

Security artifacts can themselves reveal architecture, vulnerabilities,
internal registry names, tenant identifiers, or incident details. Sanitize
evidence before publishing. Do not paste credentials into the threat model.

## Predict before running

Create `artifacts/predictions.md`:

1. Which claim does a SHA-256 digest prove?
2. Does a valid digest prove a license is acceptable?
3. Will adding one byte to a file change its digest?
4. Why is an undeclared bundle file rejected?
5. Does ClusterIP authenticate a user?
6. Does NetworkPolicy authorize a tenant's document?
7. Why is anonymous denial tested before restricted content is attached?
8. What risk remains with safetensors?
9. Which service-account token does the sample mount?
10. Which negative fixture controls should the static verifier reject?

Keep predictions unchanged.

## Lab outline

1. Inventory platform assets, principals, and data flows.
2. Build and verify a small provenance bundle.
3. Inspect restricted Kubernetes controls.
4. Threat-model artifact, identity, network, RAG, and deletion paths.
5. Tamper with one artifact and verify failure.
6. Reject an unsafe deployment fixture.
7. Define authentication/authorization denial tests.
8. Optionally test network/admission behavior in a disposable cluster.

## Step-by-step lab

### 1. Build the provenance bundle

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected shape:

```text
provenance=.../bundle/provenance.json artifacts=3
PASS: 3 declared bundle artifacts match exact hashes ...
PASS: private, digest-pinned, restricted workload controls are present
```

Inspect:

```bash
python3 -m json.tool artifacts/bundle/provenance.json
```

Pick one file and verify manually:

```bash
shasum -a 256 artifacts/bundle/model-card.json
```

Compare the digest with the provenance record. On Linux, `sha256sum` is the
equivalent command.

### 2. Inspect the exact file-set gate

Add an undeclared file:

```bash
printf '{}\n' > artifacts/bundle/unreviewed.json
set +e
python3 src/verify_provenance.py \
  --config configs/bundle.json \
  --provenance artifacts/bundle/provenance.json \
  --bundle-dir artifacts/bundle
status=$?
set -e
test "$status" -ne 0
rm artifacts/bundle/unreviewed.json
```

Fail-closed file sets prevent a valid manifest from coexisting with an
unreviewed sidecar artifact.

### 3. Inspect Kubernetes controls

```bash
python3 scripts/verify-k8s-security.py \
  --manifest k8s/restricted-workload.yaml
```

Trace each marker to the manifest. Explain why the Service and NetworkPolicy do
not complete authentication.

Inspect the admission example:

```bash
sed -n '1,260p' policies/validating-admission-policy.yaml
```

The binding selects only namespaces explicitly labeled for the course policy.
The policy uses `failurePolicy: Fail`. Test CEL compatibility and recovery in a
disposable cluster before operational use.

### 4. Write the threat model

```bash
cp THREAT-MODEL-TEMPLATE.md artifacts/threat-model.md
```

Add at least these abuse cases:

- model/image/revision substitution;
- poisoned training or retrieval source;
- unsafe checkpoint deserialization;
- prompt injection triggering a tool;
- cross-tenant chunk retrieval;
- static cloud credential theft;
- public unauthenticated endpoint;
- model extraction/denial of service;
- prompt/response leakage in telemetry;
- incomplete data deletion.

Every row needs a verification method and residual-risk owner.

### 5. Write the auth release test

Copy `AUTH-RELEASE-GATE.md` into your deployment runbook. Specify the intended
caller and concrete platform-native mechanism. Record:

- anonymous result;
- authenticated unauthorized result;
- authorized minimal action;
- cross-tenant denial;
- token/credential audience and lifetime;
- action-level policy;
- audit trail;
- revocation/rollback.

Do not attach private data until denial is proven.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-tamper-failure.txt
cat artifacts/expected-policy-failure.txt
```

The first failure appends bytes to the model card after provenance generation.
Hash and size checks fail. The second inspects a negative Kubernetes fixture and
reports missing restrictions plus public/privileged settings.

Recovery regenerates the bundle from reviewed fixtures:

```bash
./scripts/run-cpu-lab.sh
```

Do not “repair” a tampered artifact by updating the digest before source,
review, license, and intended change have been established. A new legitimate
artifact receives a new provenance statement and release decision.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/bundle/provenance.json >/dev/null
```

Verify no obvious unsafe controls leaked into the safe manifest:

```bash
test -z "$(
  grep -E 'type: LoadBalancer|hostNetwork: true|privileged: true|:latest' \
    k8s/restricted-workload.yaml || true
)"
```

Optional cluster verification includes:

- restricted admission rejects a deliberately nonconforming Pod;
- default-deny blocks an unrelated test Pod;
- allowed gateway path works;
- DNS works and unintended egress fails;
- no Kubernetes API token is mounted;
- anonymous public reachability is absent;
- identity gateway returns identifiable 401/403 before content;
- cross-tenant authorization fails.

Record CNI/admission versions and do not infer NetworkPolicy enforcement merely
from successful object creation.

## Troubleshooting

If provenance fails immediately, compare exact file bytes, sizes, symlink
status, and undeclared files. Line-ending conversion changes hashes.

If a license is not allowlisted, stop and verify origin/terms. Adding a string
to the allowlist is not legal review.

If a Pod is rejected by restricted admission, inspect UID, seccomp,
capabilities, privilege escalation, host namespaces, volumes, and image.
Avoid weakening the namespace label as the first fix.

If NetworkPolicy objects apply but traffic remains open, confirm the cluster
network provider enforces the API and inspect policy selection. An object
existing is not enforcement proof.

If model download fails after default-deny, that is expected unless an explicit
private artifact path is allowed. Prefer pre-staged immutable artifacts or a
narrow private endpoint; do not add unrestricted internet egress casually.

If an identity gate allows anonymous content, stop deployment. Remove or detach
restricted content, fix the gate, and re-run anonymous and unauthorized denial.

If the app requires Kubernetes API access, enable a dedicated service-account
token only with a minimal Role/RoleBinding and short projected token audience.
Do not restore the default token without explaining the permission.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── bundle/
│   ├── model-card.json
│   ├── adapter-config.json
│   ├── index-manifest.json
│   └── provenance.json
├── expected-tamper-failure.txt
├── expected-policy-failure.txt
├── threat-model.md
├── identity-and-authz.md
├── anonymous-denial.txt
├── unauthorized-denial.txt
├── admission-tests.txt
├── network-policy-tests.txt
├── deletion-map.md
└── residual-risk.md
```

Sanitize cluster names, accounts, internal endpoints, tokens, prompts, and
document content before sharing.

## Exercises

1. Add an undeclared `.pkl` fixture and prove both file-set and format gates
   reject it.
2. Add a detached signature/identity verification step using an approved
   signing system; explain what identity is established.
3. Generate an SBOM for a lesson image and compare it with provenance.
4. Add an EKS workload identity with one read-only private object prefix; prove
   other prefixes/actions fail.
5. Create an external test Pod and verify default-deny, then the intended
   gateway path.
6. Add retrieval service egress without allowing the whole namespace or VPC.
7. Build a cross-tenant query test that must return zero unauthorized chunks.
8. Add a malicious retrieved document and prove it cannot change tool policy.
9. Threat-model adapter hot-loading and multi-tenant LoRA routing.
10. Map complete deletion across object versions, snapshots, indexes, caches,
    telemetry, and backups.
11. Define an incident response for leaked model endpoint credentials.
12. Verify anonymous denial before and after attaching a harmless public
    fixture, then remove it.

## Completion gate

You are done when:

- provenance verification passes for reviewed bytes and fails after tampering;
- the exact bundle file set is enforced;
- the unsafe Kubernetes fixture is rejected;
- the safe manifest is private, digest-pinned, non-root, read-only, token-free,
  and default-deny;
- your threat register covers supply chain, identity, network, model, data, RAG,
  telemetry, availability, and deletion;
- authentication and authorization are concrete for the intended caller;
- anonymous and cross-tenant denial are release gates;
- every residual risk has an owner and verification plan;
- no static credentials or private identifiers enter the repository.

## Cleanup

Local:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

Optional cluster:

```bash
kubectl delete namespace oms-lesson-47 --ignore-not-found
kubectl get namespace oms-lesson-47
```

Remove any test identity relationships, roles, policies, credentials, malicious
documents, object versions, admission bindings, and telemetry created for the
lab. Verify deletion through the owning API. Restore no public access.

## Primary references

Sources were reviewed on 2026-10-21:

- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Kubernetes service accounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [AWS Signature Version 4](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html)
- [EKS Pod Identities](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [SLSA provenance](https://slsa.dev/spec/v1.2/provenance)
- [Sigstore documentation](https://docs.sigstore.dev/)
- [Safetensors format](https://huggingface.co/docs/safetensors/)
- [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The local provenance and static policy paths are author-validated. The sample
does not claim a live cluster, identity gateway, AWS authorization, CNI policy,
admission controller, signature system, or vulnerability scanner was validated.
