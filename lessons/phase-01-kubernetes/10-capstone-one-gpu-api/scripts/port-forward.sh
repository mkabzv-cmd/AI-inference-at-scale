#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
local_port="${LOCAL_PORT:-18000}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_eks_target
assert_safe_release_name
assert_namespace_owned_or_absent

service="$(
  kubectl -n "$namespace" get service \
    -l "app.kubernetes.io/instance=${release}" \
    -o jsonpath='{.items[0].metadata.name}'
)"
if [[ -z "$service" ]]; then
  printf 'no Service found for Helm release %s\n' "$release" >&2
  exit 1
fi

printf 'forwarding http://127.0.0.1:%s (Ctrl-C to stop)\n' "$local_port"
kubectl -n "$namespace" port-forward \
  "service/${service}" "${local_port}:80"
