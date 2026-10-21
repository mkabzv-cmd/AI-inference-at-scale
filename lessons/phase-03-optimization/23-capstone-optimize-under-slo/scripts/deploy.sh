#!/usr/bin/env bash
set -euo pipefail

: "${CONFIRM_LAB_CONTEXT:?set to the exact intended kubectl context}"
candidate="${1:?usage: $0 CANDIDATE_ID}"
if [[ ! "$candidate" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#candidate} > 63 )); then
  printf 'candidate ID must be a Kubernetes-safe name\n' >&2
  exit 2
fi
context="$(kubectl config current-context)"
[[ "$context" == "$CONFIRM_LAB_CONTEXT" ]] || {
  echo "refusing context $context; expected $CONFIRM_LAB_CONTEXT" >&2
  exit 2
}
manifest="artifacts/${candidate}.yaml"
[[ -f "$manifest" ]] || {
  echo "render first: ./scripts/render-deployment.sh $candidate" >&2
  exit 2
}
grep -q 'type: ClusterIP' "$manifest"
if grep -Eq \
  '^[[:space:]]*(type:[[:space:]]*(LoadBalancer|NodePort|ExternalName)|host(Network|PID|IPC):[[:space:]]*true|externalIPs:)' \
  "$manifest"; then
  echo "refusing an externally exposed or host-networked manifest" >&2
  exit 2
fi
kubectl apply --dry-run=client -f "$manifest" >/dev/null
kubectl create namespace oms-lesson-23 --dry-run=client -o yaml |
  kubectl apply -f -
kubectl label namespace oms-lesson-23 \
  app.kubernetes.io/part-of=oms-course --overwrite
kubectl apply --dry-run=server -f "$manifest" >/dev/null
kubectl apply -f "$manifest"
kubectl rollout status \
  "deployment/vllm" \
  --namespace oms-lesson-23 \
  --timeout=25m
kubectl get pod,service -n oms-lesson-23 -o wide
