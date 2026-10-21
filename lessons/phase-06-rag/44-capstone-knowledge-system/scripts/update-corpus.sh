#!/usr/bin/env bash
set -euo pipefail

: "${COURSE_NAMESPACE:?Set COURSE_NAMESPACE}"
kubectl -n "$COURSE_NAMESPACE" patch configmap knowledge-service-config \
  --type merge \
  --patch '{"data":{"COURSE_CORPUS_RELATIVE":"data/corpus-v2.jsonl"}}'
kubectl -n "$COURSE_NAMESPACE" rollout restart deployment/knowledge-service
kubectl -n "$COURSE_NAMESPACE" rollout status deployment/knowledge-service \
  --timeout=180s
kubectl -n "$COURSE_NAMESPACE" get configmap knowledge-service-config \
  -o jsonpath='{.data.COURSE_CORPUS_RELATIVE}{"\n"}'
