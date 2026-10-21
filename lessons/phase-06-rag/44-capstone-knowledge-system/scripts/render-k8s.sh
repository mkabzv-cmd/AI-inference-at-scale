#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${IMAGE_REF:?Set IMAGE_REF to repository@sha256:<64 lowercase hex>}"
: "${COURSE_NAMESPACE:?Set COURSE_NAMESPACE to an existing namespace}"
python3 "$lesson_dir/src/render_k8s.py" \
  --template "$lesson_dir/k8s/knowledge-service.yaml.tmpl" \
  --image "$IMAGE_REF" \
  --namespace "$COURSE_NAMESPACE" \
  --output "$lesson_dir/artifacts/rendered-knowledge-service.yaml"
