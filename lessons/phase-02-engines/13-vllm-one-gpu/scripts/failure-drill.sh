#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l13}"
mkdir -p artifacts
kubectl patch deployment/vllm -n "$LAB_NAMESPACE" --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/args/11","value":"1.20"}]'
set +e
kubectl rollout status deployment/vllm -n "$LAB_NAMESPACE" --timeout=3m \
  >artifacts/failure-rollout.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "expected invalid gpu-memory-utilization rollout to fail" >&2
  exit 1
fi
kubectl get pods -n "$LAB_NAMESPACE" -o wide >artifacts/failure-pods.txt
kubectl logs -n "$LAB_NAMESPACE" deployment/vllm --tail=200 \
  >artifacts/failure.log 2>&1 || true
grep -Ei 'gpu.memory.utilization|must be|invalid|value' artifacts/failure.log
kubectl rollout undo deployment/vllm -n "$LAB_NAMESPACE"
kubectl rollout status deployment/vllm -n "$LAB_NAMESPACE" --timeout=25m
printf 'failure diagnosed and rollout repaired\n'
