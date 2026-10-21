#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
manifest="artifacts/rendered.yaml"
[[ -f "$manifest" ]] || {
  printf 'missing %s; run render-k8s.py first\n' "$manifest" >&2
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
  course.lesson=24 --overwrite
kubectl -n "$LAB_NAMESPACE" create configmap collectives-source \
  --from-file=collectives_lab.py=src/collectives_lab.py \
  --dry-run=client -o yaml |
  kubectl apply -f -
kubectl apply --dry-run=server -f "$manifest" >/dev/null
kubectl apply -f "$manifest"
kubectl -n "$LAB_NAMESPACE" rollout status statefulset/collectives \
  --timeout=15m

for ordinal in 0 1 2; do
  kubectl -n "$LAB_NAMESPACE" wait \
    --for=condition=Ready \
    "pod/collectives-${ordinal}" \
    --timeout=10m
  kubectl -n "$LAB_NAMESPACE" logs "collectives-${ordinal}" |
    grep -q '"event": "RESULT_JSON"'
done
printf '[ok] all three rank Pods completed successfully\n'
