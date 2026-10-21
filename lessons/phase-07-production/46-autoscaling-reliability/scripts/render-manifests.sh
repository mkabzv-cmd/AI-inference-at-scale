#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"

: "${LAB_NAMESPACE:?Set LAB_NAMESPACE to a dedicated oms-lesson-46-* namespace}"
: "${MODEL_IMAGE:?Set MODEL_IMAGE to an immutable image@sha256:digest reference}"
: "${PROMETHEUS_URL:?Set PROMETHEUS_URL to the private in-cluster Prometheus URL}"

if [[ ! "$LAB_NAMESPACE" =~ ^oms-lesson-46-[a-z0-9-]+$ ]]; then
  printf 'LAB_NAMESPACE must start with oms-lesson-46-\n' >&2
  exit 1
fi
if [[ ! "$MODEL_IMAGE" =~ ^[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}$ ]]; then
  printf 'MODEL_IMAGE must be immutable and end in @sha256:<64 hex>\n' >&2
  exit 1
fi
if [[ ! "$PROMETHEUS_URL" =~ ^https?://[a-z0-9]([-a-z0-9.]*[a-z0-9])?\.svc(\.cluster\.local)?(:[0-9]{1,5})?$ ]]; then
  printf 'PROMETHEUS_URL must be a private Kubernetes service URL\n' >&2
  exit 1
fi

mkdir -p "$artifact_dir/rendered"
for template in \
  workload.yaml.tpl \
  hpa-custom-metric.yaml.tpl \
  keda-scaledobject.yaml.tpl
do
  output="$artifact_dir/rendered/${template%.tpl}"
  sed \
    -e "s|__NAMESPACE__|$LAB_NAMESPACE|g" \
    -e "s|__MODEL_IMAGE__|$MODEL_IMAGE|g" \
    -e "s|__PROMETHEUS_URL__|$PROMETHEUS_URL|g" \
    "$lesson_dir/k8s/$template" >"$output"
done

printf 'Rendered manifests under %s\n' "$artifact_dir/rendered"
