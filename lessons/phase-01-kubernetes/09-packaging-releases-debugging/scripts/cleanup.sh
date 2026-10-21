#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-packaging-lab}"
release="${HELM_RELEASE:-course}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_target
assert_safe_release_name
assert_namespace_owned_or_absent

if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'release and namespace are already absent\n'
  exit 0
fi

release_found="$(
  helm list --namespace "$namespace" --all \
    --filter "^${release}$" --short
)"
if [[ -n "$release_found" ]]; then
  helm uninstall "$release" --namespace "$namespace" --wait --timeout 3m
else
  printf 'Helm release %s is already absent\n' "$release"
fi
kubectl delete namespace "$namespace" --ignore-not-found --wait=true

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'namespace still exists: %s\n' "$namespace" >&2
  exit 1
fi
printf 'release and namespace removed\n'
