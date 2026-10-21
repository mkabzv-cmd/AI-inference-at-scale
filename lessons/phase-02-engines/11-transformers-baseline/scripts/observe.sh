#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l11}"
mkdir -p artifacts
kubectl get all,pvc -n "$LAB_NAMESPACE" -o wide >artifacts/kubernetes.txt
kubectl get events -n "$LAB_NAMESPACE" \
  --sort-by=.metadata.creationTimestamp >artifacts/events.txt
kubectl logs -n "$LAB_NAMESPACE" deployment/transformers-baseline \
  >artifacts/server.log
kubectl exec -n "$LAB_NAMESPACE" deployment/transformers-baseline -- \
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu \
  --format=csv,noheader >artifacts/nvidia-smi.csv
kubectl exec -n "$LAB_NAMESPACE" deployment/transformers-baseline -- \
  cat /app/dependency-versions.txt >artifacts/dependency-versions.txt
printf 'evidence written under artifacts/\n'
