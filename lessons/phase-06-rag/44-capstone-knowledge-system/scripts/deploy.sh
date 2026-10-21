#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${COURSE_NAMESPACE:?Set COURSE_NAMESPACE to an existing namespace}"
kubectl config current-context
kubectl get namespace "$COURSE_NAMESPACE" >/dev/null
"$lesson_dir/scripts/render-k8s.sh"
kubectl apply -f "$lesson_dir/artifacts/rendered-knowledge-service.yaml"
kubectl -n "$COURSE_NAMESPACE" rollout status deployment/knowledge-service \
  --timeout=180s
