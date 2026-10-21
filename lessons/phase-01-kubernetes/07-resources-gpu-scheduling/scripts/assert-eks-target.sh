#!/usr/bin/env bash
set -euo pipefail

namespace="gpu-scheduling"
expected_part_of="open-model-systems-course"
expected_lesson="07"

assert_eks_target() {
  : "${AWS_REGION:?set AWS_REGION to the intended EKS region}"
  : "${EKS_CLUSTER:?set EKS_CLUSTER to the intended lab cluster}"
  : "${GPU_NODEGROUP:?set GPU_NODEGROUP to the intended managed node group}"

  if [[ "${CONFIRM_GPU_NODEGROUP:-}" != "$GPU_NODEGROUP" ]]; then
    printf 'set CONFIRM_GPU_NODEGROUP to the exact node-group name: %s\n' \
      "$GPU_NODEGROUP" >&2
    return 1
  fi

  for command_name in aws kubectl python3; do
    command -v "$command_name" >/dev/null 2>&1 || {
      printf 'missing required command: %s\n' "$command_name" >&2
      return 1
    }
  done

  local expected_server
  local active_server
  local context
  local nodegroup_json
  expected_server="$(
    aws eks describe-cluster \
      --region "$AWS_REGION" \
      --name "$EKS_CLUSTER" \
      --query 'cluster.endpoint' \
      --output text
  )"
  active_server="$(
    kubectl config view --minify \
      -o jsonpath='{.clusters[0].cluster.server}'
  )"
  context="$(kubectl config current-context)"

  if [[ -z "$expected_server" || "$expected_server" == "None" ||
    -z "$active_server" || "$active_server" != "$expected_server" ]]; then
    printf 'refusing Kubernetes target mismatch\n' >&2
    printf '  context:  %s\n' "$context" >&2
    printf '  current:  %s\n' "${active_server:-<none>}" >&2
    printf '  expected: %s\n' "${expected_server:-<none>}" >&2
    return 1
  fi

  nodegroup_json="$(
    aws eks describe-nodegroup \
      --cluster-name "$EKS_CLUSTER" \
      --nodegroup-name "$GPU_NODEGROUP" \
      --region "$AWS_REGION" \
      --query 'nodegroup.{status:status,scaling:scalingConfig,instanceTypes:instanceTypes}' \
      --output json
  )"
  python3 -c '
import json
import sys

group = json.load(sys.stdin)
scaling = group.get("scaling") or {}
status = group.get("status")
minimum = scaling.get("minSize")
maximum = scaling.get("maxSize")
desired = scaling.get("desiredSize")
instance_types = group.get("instanceTypes") or []

if status != "ACTIVE":
    raise SystemExit(f"managed node group is not ACTIVE: {status!r}")
if minimum != 0:
    raise SystemExit(f"lab requires minSize=0; found {minimum!r}")
if not isinstance(maximum, int) or maximum < 1:
    raise SystemExit(f"lab requires maxSize>=1; found {maximum!r}")
if desired not in (0, 1):
    raise SystemExit(f"refusing node group with desiredSize={desired!r}; expected 0 or 1")
print(
    "verified node group: "
    f"status={status} min={minimum} max={maximum} desired={desired} "
    f"instanceTypes={instance_types}"
)
' <<<"$nodegroup_json"

  printf 'verified EKS target: %s (%s)\n' "$EKS_CLUSTER" "$context"
}

assert_namespace_owned_or_absent() {
  local found
  local part_of
  local lesson
  found="$(kubectl get namespace "$namespace" --ignore-not-found -o name)"
  if [[ -z "$found" ]]; then
    printf 'lesson namespace is absent: %s\n' "$namespace"
    return 0
  fi

  part_of="$(
    kubectl get namespace "$namespace" \
      -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}'
  )"
  lesson="$(
    kubectl get namespace "$namespace" \
      -o jsonpath='{.metadata.labels.lesson\.open-model-systems/id}'
  )"
  if [[ "$part_of" != "$expected_part_of" || "$lesson" != "$expected_lesson" ]]; then
    printf 'refusing namespace %s with unexpected ownership labels\n' \
      "$namespace" >&2
    printf '  part-of=%s lesson=%s\n' \
      "${part_of:-<missing>}" "${lesson:-<missing>}" >&2
    return 1
  fi
  printf 'verified lesson namespace ownership: %s\n' "$namespace"
}

if [[ "${BASH_SOURCE[0]:-}" == "$0" ]]; then
  assert_eks_target
  assert_namespace_owned_or_absent
  printf 'Lesson 07 EKS target checks passed.\n'
fi
