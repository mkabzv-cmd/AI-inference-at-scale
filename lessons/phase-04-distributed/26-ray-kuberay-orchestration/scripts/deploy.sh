#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
[[ -f artifacts/raycluster.yaml ]] || {
  printf 'run scripts/render.py first\n' >&2
  exit 2
}
manifest=artifacts/raycluster.yaml
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
  course.lesson=26 --overwrite
kubectl -n "$LAB_NAMESPACE" create configmap lesson-26-source \
  --from-file=gpu_placement.py=src/gpu_placement.py \
  --dry-run=client -o yaml |
  kubectl apply -f -
kubectl apply --dry-run=server -f "$manifest" >/dev/null
kubectl apply -f "$manifest"

kubectl -n "$LAB_NAMESPACE" wait \
  --for=condition=RayClusterProvisioned \
  raycluster/teaching-ray \
  --timeout=15m
kubectl -n "$LAB_NAMESPACE" wait \
  --for=condition=Ready pod \
  -l ray.io/cluster=teaching-ray \
  --timeout=10m
