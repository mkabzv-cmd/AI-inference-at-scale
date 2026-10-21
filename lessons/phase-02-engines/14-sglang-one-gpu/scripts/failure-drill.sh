#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l14}"
mkdir -p artifacts
kubectl patch deployment/sglang -n "$LAB_NAMESPACE" --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/args/11","value":"1.20"}]'
set +e
kubectl rollout status deployment/sglang -n "$LAB_NAMESPACE" --timeout=3m \
  >artifacts/failure-rollout.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "expected invalid mem-fraction-static to fail" >&2
  exit 1
fi
kubectl get pods -n "$LAB_NAMESPACE" >artifacts/failure-pods.txt
kubectl logs -n "$LAB_NAMESPACE" deployment/sglang --tail=200 \
  >artifacts/failure.log 2>&1 || true
grep -Ei 'mem.fraction|assert|invalid|value|memory' artifacts/failure.log
kubectl rollout undo deployment/sglang -n "$LAB_NAMESPACE"
kubectl rollout status deployment/sglang -n "$LAB_NAMESPACE" --timeout=25m
printf 'failure diagnosed and repaired\n'
