# Lesson 49 exercise guidance

These are review criteria and example reasoning. Your values must come from
your own frozen workload, release, environment, and evidence.

## Three-node arithmetic

With one GPU on each of three nodes, TP=3/PP=1 or TP=1/PP=3 can split one model
across three workers when the selected engine/version supports it. DP=3 creates
three copies; it may raise aggregate throughput but does not make one oversized
copy fit. For the capstone's model-splitting topology, TP×PP must equal three
and DP must equal one. Record actual rank placement and network rather than
assuming arithmetic proves execution.

## Mutable image overlay

Change `/image` in `release.json` from `repository@sha256:<64 hex>` to a tag.
Expected violations include `MUTABLE_IMAGE` and `HASH_MISMATCH`. The second
failure matters: even a syntactically valid replacement is not the indexed
release.

## Claim-scope overlay

Change `/claim_scope` in one evidence file. Expect
`EVIDENCE_SCOPE_MISMATCH`, `GATE_HASH_MISMATCH`, and `HASH_MISMATCH`.
Performance measured for another workload/hardware boundary cannot support this
release.

## ITL and queue limits

Add predeclared p95 inter-token latency and p95 queue-wait limits to both the
template and verifier. Keep client/server measurement boundaries explicit.
Require raw streaming timestamps rather than deriving ITL from a non-streaming
total.

## Multi-slice quality

Represent slices as named objects with direction, threshold, sample count,
baseline, candidate, and criticality. Reject any critical slice failure. Avoid
averaging a safety regression into a higher overall score.

## Three-node worker loss

If every request needs all ranks, one worker loss normally makes that replica
unavailable; reject new work and recover/restart the group. Degraded serving is
possible only if an independent healthy replica or an intentionally smaller
fallback release exists. A timeout is not graceful degradation.

## Attached versus merged adapters

Attached adapters are small and can share a base, but require engine support,
compatible routing, and adapter/base binding. Merged releases are larger and
behave like ordinary model weights, but must preserve transformation provenance
and repeat evaluation. Keep both rollback artifacts immutable if both can be
served.

## RAG update and rollback

Use versioned corpus, chunker, embedding, and index manifests. Promote the index
as part of the same release or through an explicitly compatible contract.
Rollback must restore source/index identity and behavior while retaining tenant
authorization before prompt construction.

## Signed provenance

A valid signature can establish that an expected identity signed expected
bytes under a policy. It does not prove quality, safety, license permission, or
absence of vulnerabilities. Keep those as separate gates.

## Kubernetes policy extension

Parse rendered YAML with a real YAML/Kubernetes policy tool in the extension.
Require digest-pinned images plus CPU, memory, and GPU requests/limits where
applicable. Retain the lesson text scanner as a dependency-free first gate, not
as the authoritative parser.

## Canary design

A sound canary records stable/candidate identity, comparable traffic,
predeclared minimum samples/window, latency/error/queue/quality guardrails, and
automatic/operator stop conditions. Restricted traffic enters only after the
candidate path passes authentication and authorization denial tests.

## AWS cleanup inventory

At minimum consider EKS namespace objects, Pods/Jobs, node groups or
provisioners, Auto Scaling groups/instances, EBS volumes/snapshots, EFS,
load balancers/target groups, addresses, object versions, ECR images,
CloudWatch logs/metrics/alarms, and experiment-created IAM/network resources.
Scope every query by recorded tags/IDs and return shared resources to their
starting state rather than deleting them.

## Evidence-only review

An independent reviewer should be able to establish byte consistency, declared
threshold results, topology arithmetic, and the presence of required controls.
They cannot establish the truth of external observations from unsigned local
JSON alone. That gap motivates protected raw evidence, signed provenance,
audit logs, and independent reproduction.

## Post-finalization mutation

Changing one indexed file produces an index hash mismatch. If it is a gate
file, it also produces a release gate hash mismatch. If a cross-artifact field
changes, a semantic mismatch appears too. Repair by reviewing the change,
rerunning affected gates, issuing a new release/evidence revision, and
finalizing again.

## Retrospective

A useful retrospective names the prediction, observed evidence, causal
mechanism, decision, uncertainty, and follow-up. “Optimization X was faster”
is incomplete without workload, quality, hardware, version, and variance
boundaries.
