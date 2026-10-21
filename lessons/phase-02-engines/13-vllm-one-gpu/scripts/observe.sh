#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l13}"
mkdir -p artifacts
kubectl get all,pvc -n "$LAB_NAMESPACE" -o wide >artifacts/kubernetes.txt
kubectl get events -n "$LAB_NAMESPACE" \
  --sort-by=.metadata.creationTimestamp >artifacts/events.txt
kubectl logs -n "$LAB_NAMESPACE" deployment/vllm >artifacts/vllm.log
kubectl exec -n "$LAB_NAMESPACE" deployment/vllm -- \
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu \
  --format=csv,noheader >artifacts/nvidia-smi.csv
kubectl get deployment/vllm -n "$LAB_NAMESPACE" -o yaml \
  >artifacts/deployment.yaml
printf 'observation bundle written\n'
