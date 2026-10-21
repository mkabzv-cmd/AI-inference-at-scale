#!/usr/bin/env bash
set -euo pipefail

required_vars=(AWS_REGION EKS_CLUSTER GPU_NODEGROUP LAB_NAMESPACE)
for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf '[fail] required environment variable is unset: %s\n' "$name" >&2
    exit 2
  fi
done

for command_name in aws kubectl python3; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf '[fail] required command not found: %s\n' "$command_name" >&2
    exit 2
  }
done

if [[ ! "$LAB_NAMESPACE" =~ ^oms-distributed-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#LAB_NAMESPACE} > 63 )); then
  printf '%s\n' \
    '[fail] LAB_NAMESPACE must be a DNS label beginning oms-distributed-' >&2
  exit 2
fi

if [[ "${CONFIRM_GPU_NODEGROUP:-}" != "$GPU_NODEGROUP" ]]; then
  printf '[fail] set CONFIRM_GPU_NODEGROUP to the exact value %s\n' \
    "$GPU_NODEGROUP" >&2
  exit 3
fi

expected_endpoint="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER" \
    --query 'cluster.endpoint' \
    --output text
)"
active_endpoint="$(
  kubectl config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}'
)"
active_context="$(kubectl config current-context)"
if [[ -z "$expected_endpoint" || "$expected_endpoint" == "None" ]]; then
  printf '[fail] could not resolve EKS endpoint for %s\n' "$EKS_CLUSTER" >&2
  exit 1
fi
if [[ "$active_endpoint" != "$expected_endpoint" ]]; then
  printf '[fail] kubectl context %s targets a different API endpoint\n' \
    "$active_context" >&2
  printf '  active:   %s\n  expected: %s\n' \
    "$active_endpoint" "$expected_endpoint" >&2
  exit 1
fi

namespace_json="$(
  kubectl get namespace "$LAB_NAMESPACE" --ignore-not-found -o json
)"
if [[ -n "$namespace_json" ]]; then
  NAMESPACE_JSON="$namespace_json" python3 - "$LAB_NAMESPACE" <<'PY'
import json
import os
import sys

namespace = json.loads(os.environ["NAMESPACE_JSON"])
expected = sys.argv[1]
metadata = namespace.get("metadata", {})
labels = metadata.get("labels", {})
if metadata.get("name") != expected:
    raise SystemExit("[fail] Kubernetes returned an unexpected namespace")
if labels.get("app.kubernetes.io/part-of") != "oms-distributed-course":
    raise SystemExit(
        "[fail] existing namespace is not owned by this distributed lab"
    )
print("[ok] existing namespace ownership label is valid")
PY
fi

printf '[ok] AWS caller: '
aws sts get-caller-identity --query Arn --output text
printf '[ok] kubectl context: %s\n' "$active_context"
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query \
  'nodegroup.{status:status,instances:instanceTypes,scaling:scalingConfig}' \
  --output table

for permission in \
  'get nodes' \
  'create namespaces' \
  'create pods' \
  'create statefulsets.apps' \
  'create services' \
  'create configmaps'; do
  verb="${permission%% *}"
  resource="${permission#* }"
  if ! kubectl auth can-i "$verb" "$resource" \
    --namespace "$LAB_NAMESPACE" | grep -qx yes; then
    printf '[fail] missing Kubernetes permission: %s %s\n' \
      "$verb" "$resource" >&2
    exit 1
  fi
done

printf '[ok] target and basic permissions passed\n'
