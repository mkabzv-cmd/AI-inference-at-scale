#!/usr/bin/env bash
set -euo pipefail

assert_safe_namespace_name() {
  : "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"

  if (( ${#LAB_NAMESPACE} > 63 )) ||
    [[ ! "$LAB_NAMESPACE" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]]; then
    printf '%s\n' \
      '[fail] LAB_NAMESPACE must be a DNS label beginning with open-models-.' >&2
    return 1
  fi
}

assert_kube_context_matches_cluster() {
  : "${AWS_REGION:?Set AWS_REGION}"
  : "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"

  local expected_endpoint
  local current_endpoint
  local current_context

  expected_endpoint="$(
    aws eks describe-cluster \
      --region "$AWS_REGION" \
      --name "$EKS_CLUSTER_NAME" \
      --query 'cluster.endpoint' \
      --output text
  )"
  current_context="$(kubectl config current-context)"
  current_endpoint="$(
    kubectl config view \
      --minify \
      -o jsonpath='{.clusters[0].cluster.server}'
  )"

  if [[ -z "$expected_endpoint" || "$expected_endpoint" == "None" ]]; then
    printf '[fail] could not resolve the expected EKS API endpoint\n' >&2
    return 1
  fi
  if [[ -z "$current_endpoint" ]]; then
    printf '[fail] current kubectl context has no cluster endpoint\n' >&2
    return 1
  fi
  if [[ "$current_endpoint" != "$expected_endpoint" ]]; then
    printf '[fail] kubectl context does not target the named EKS cluster\n' >&2
    printf '  context:  %s\n' "$current_context" >&2
    printf '  current:  %s\n' "$current_endpoint" >&2
    printf '  expected: %s\n' "$expected_endpoint" >&2
    return 1
  fi

  printf '[ok] kubectl context %s matches EKS cluster %s\n' \
    "$current_context" "$EKS_CLUSTER_NAME"
}

assert_namespace_owned_or_absent() {
  : "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"

  local namespace_json
  namespace_json="$(
    kubectl get namespace "$LAB_NAMESPACE" \
      --ignore-not-found \
      -o json
  )"
  if [[ -z "$namespace_json" ]]; then
    printf '[ok] namespace is absent and available for this lab: %s\n' \
      "$LAB_NAMESPACE"
    return 0
  fi

  python3 -c '
import json
import sys

expected_name = sys.argv[1]
namespace = json.load(sys.stdin)
metadata = namespace.get("metadata", {})
labels = metadata.get("labels", {})

if metadata.get("name") != expected_name:
    raise SystemExit("[fail] Kubernetes returned an unexpected namespace")
if labels.get("app.kubernetes.io/part-of") != "open-model-systems-learning":
    raise SystemExit(
        "[fail] existing namespace is not owned by open-model-systems-learning"
    )
if labels.get("course.lesson") != "04":
    raise SystemExit("[fail] existing namespace is not labeled for lesson 04")
print(f"[ok] existing namespace has the expected lesson ownership: {expected_name}")
' "$LAB_NAMESPACE" <<<"$namespace_json"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  for command_name in aws kubectl python3; do
    command -v "$command_name" >/dev/null 2>&1 || {
      printf '[fail] required command not found: %s\n' "$command_name" >&2
      exit 2
    }
  done
  assert_safe_namespace_name
  assert_kube_context_matches_cluster
  assert_namespace_owned_or_absent
  printf 'Target safety checks passed.\n'
fi
