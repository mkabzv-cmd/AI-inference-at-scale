#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
manifest=artifacts/vllm-pp-raycluster.yaml
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

kubectl create namespace "$LAB_NAMESPACE" \
  --dry-run=client -o yaml |
  kubectl apply -f -
kubectl label namespace "$LAB_NAMESPACE" \
  app.kubernetes.io/part-of=oms-distributed-course \
  course.lesson=29 --overwrite
kubectl -n "$LAB_NAMESPACE" create configmap lesson-29-source \
  --from-file=download_model.py=src/download_model.py \
  --dry-run=client -o yaml |
  kubectl apply -f -
kubectl apply --dry-run=server -f "$manifest" >/dev/null
kubectl apply -f "$manifest"
kubectl -n "$LAB_NAMESPACE" wait \
  --for=condition=RayClusterProvisioned raycluster/vllm-pp \
  --timeout=60m
kubectl -n "$LAB_NAMESPACE" wait --for=condition=Ready pod \
  -l ray.io/cluster=vllm-pp --timeout=15m
