#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
manifest=artifacts/network-benchmark.yaml
[[ -f "$manifest" ]] || {
  printf 'missing %s; run scripts/render.py first\n' "$manifest" >&2
  exit 2
}
if grep -Eq \
  '^[[:space:]]*(type:[[:space:]]*(LoadBalancer|NodePort|ExternalName)|host(Network|PID|IPC):[[:space:]]*true|externalIPs:)' \
  "$manifest"; then
  printf 'refusing a manifest with externally reachable or host-level networking\n' >&2
  exit 1
fi
kubectl create namespace "$LAB_NAMESPACE" --dry-run=client -o yaml |
  kubectl apply -f -
kubectl label namespace "$LAB_NAMESPACE" \
  app.kubernetes.io/part-of=oms-distributed-course \
  course.lesson=27 --overwrite
kubectl -n "$LAB_NAMESPACE" create configmap lesson-27-source \
  --from-file=nccl_benchmark.py=src/nccl_benchmark.py \
  --dry-run=client -o yaml |
  kubectl apply -f -
kubectl apply --dry-run=server -f "$manifest" >/dev/null
kubectl apply -f "$manifest"
kubectl -n "$LAB_NAMESPACE" rollout status statefulset/network-benchmark \
  --timeout=20m
for ordinal in 0 1 2; do
  kubectl -n "$LAB_NAMESPACE" wait --for=condition=Ready \
    "pod/network-benchmark-${ordinal}" --timeout=15m
done
