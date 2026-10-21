# One-GPU API operational runbook

## Identifiers

- AWS account and Region:
- EKS cluster:
- GPU node group:
- Namespace:
- Helm release:
- Base image digest:
- Image digest:
- Helm-test image digest:
- Dependency-version evidence:
- Model ID:
- Model revision:
- StorageClass and PVC:

## Deploy

List exact commands and expected checkpoints.

## Verify

- Readiness:
- Model list:
- Non-streaming request:
- Streaming request:
- GPU evidence:

## Observe

- Kubernetes objects/events:
- Init-container logs:
- API logs:
- Metrics:
- GPU process/memory:

## Failure diagnosis

### Pod Pending

Commands, evidence, and actions:

### Init container failing

Commands, evidence, and actions:

### Container crashing

Commands, evidence, and actions:

### Running but Unready

Commands, evidence, and actions:

### Ready but unreachable

Commands, evidence, and actions:

### HTTP 500 or bad output

Commands, evidence, and actions:

## Rollback

State the known-good Helm revision and behavioral verification.

## Cleanup and cost stop

List Kubernetes deletion, captured PVC/PV/EBS identifiers, EBS verification,
node-group restoration, optional ECR-image retention/deletion, and proof.
State whether `existingClaim` or `keepOnDelete` was used; never delete the
namespace while a PVC that must be preserved remains in it.
