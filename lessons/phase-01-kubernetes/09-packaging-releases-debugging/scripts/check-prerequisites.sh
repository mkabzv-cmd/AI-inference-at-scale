#!/usr/bin/env bash
set -euo pipefail

required=(kubectl helm curl docker python3)
missing=0

for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$command_name" >&2
    missing=1
  fi
done
[[ "$missing" -eq 0 ]] || exit 1

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_target
assert_namespace_owned_or_absent
namespace="$(lesson_namespace)"

require_kube_permission() {
  if ! kubectl auth can-i "$@" --quiet; then
    printf 'Kubernetes authorization denied: kubectl auth can-i %s\n' \
      "$*" >&2
    return 1
  fi
  printf 'Kubernetes authorization allows: %s\n' "$*"
}

printf 'kubectl context: %s\n' "$(kubectl config current-context)"
kubectl cluster-info
require_kube_permission create namespaces
require_kube_permission delete namespaces
require_kube_permission create configmaps --namespace "$namespace"
require_kube_permission create deployments.apps --namespace "$namespace"
require_kube_permission create secrets --namespace "$namespace"
require_kube_permission create serviceaccounts --namespace "$namespace"
require_kube_permission create services --namespace "$namespace"
helm version --short
docker version --format 'docker client={{.Client.Version}}'

helm lint chart/lesson-service
helm template course chart/lesson-service \
  --namespace "$namespace" >/dev/null
printf 'chart lint and render: OK\n'
