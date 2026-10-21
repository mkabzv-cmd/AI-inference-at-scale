#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"

required_vars=(
  AWS_REGION
  EKS_CLUSTER_NAME
  GPU_NODEGROUP_NAME
  ECR_REPOSITORY
  LAB_NAMESPACE
  IMAGE_TAG
)
for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf '[fail] required environment variable is unset: %s\n' "$name"
    exit 2
  fi
done

for name in aws kubectl docker python3 curl git; do
  command -v "$name" >/dev/null 2>&1 || {
    printf '[fail] required command not found: %s\n' "$name"
    exit 2
  }
done
printf '[ok] required local tools found\n'

aws_version="$(aws --version 2>&1)"
if [[ "$aws_version" != aws-cli/2.* ]]; then
  printf '[fail] AWS CLI v2 is required; found: %s\n' "$aws_version"
  exit 1
fi
printf '[ok] %s\n' "$aws_version"

docker info >/dev/null 2>&1 || {
  printf '[fail] Docker daemon is not reachable by this user\n'
  exit 1
}
printf '[ok] Docker daemon reachable\n'

python3 - <<'PY'
import sys
if not ((3, 9) <= sys.version_info < (3, 13)):
    raise SystemExit("[fail] validated Python range is 3.9 through 3.12")
print("[ok] Python", ".".join(map(str, sys.version_info[:3])))
PY

caller="$(aws sts get-caller-identity --query Arn --output text)"
printf '[ok] AWS caller: %s\n' "$caller"

cluster_status="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER_NAME" \
    --query 'cluster.status' \
    --output text
)"
printf '[ok] EKS cluster status: %s\n' "$cluster_status"
if [[ "$cluster_status" != "ACTIVE" ]]; then
  printf '[fail] cluster must be ACTIVE\n'
  exit 1
fi

assert_safe_namespace_name
assert_kube_context_matches_cluster
assert_namespace_owned_or_absent

require_kube_permission() {
  if ! kubectl auth can-i "$@" --quiet; then
    printf '[fail] Kubernetes authorization denied: kubectl auth can-i %s\n' \
      "$*" >&2
    return 1
  fi
  printf '[ok] Kubernetes authorization allows: %s\n' "$*"
}

require_kube_permission get pods --all-namespaces
require_kube_permission get nodes
require_kube_permission create namespaces
require_kube_permission delete namespaces
require_kube_permission create deployments.apps --namespace "$LAB_NAMESPACE"
require_kube_permission create services --namespace "$LAB_NAMESPACE"

nodegroup="$(
  aws eks describe-nodegroup \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER_NAME" \
    --nodegroup-name "$GPU_NODEGROUP_NAME" \
    --query 'nodegroup.[status,scalingConfig.desiredSize,scalingConfig.minSize,scalingConfig.maxSize,join(`,`,instanceTypes)]' \
    --output text
)"
printf '[info] node group (status desired min max types): %s\n' "$nodegroup"

printf 'Preflight complete. Manually confirm identity/context before mutations.\n'
