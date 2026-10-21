#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_eks_target
assert_safe_release_name
assert_namespace_owned_or_absent

pod="$(
  kubectl -n "$namespace" get pods \
    -l "app.kubernetes.io/instance=${release}" \
    --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{.items[-1:].metadata.name}'
)"
if [[ -z "$pod" ]]; then
  printf 'no Pod found for Helm release %s\n' "$release" >&2
  exit 1
fi
printf 'pod=%s\n' "$pod"

printf 'init-container log:\n'
kubectl -n "$namespace" logs "$pod" -c download-model || true
printf 'waiting for Pod Ready (model download/load can take minutes)...\n'
kubectl -n "$namespace" wait \
  --for=condition=Ready "pod/${pod}" --timeout=20m
kubectl -n "$namespace" rollout status \
  deployment \
  --selector "app.kubernetes.io/instance=${release}" \
  --timeout=2m
kubectl -n "$namespace" logs "$pod" -c api --tail=50
