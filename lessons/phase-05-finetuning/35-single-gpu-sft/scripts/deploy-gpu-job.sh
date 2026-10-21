#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_35_GPU_JOB:?Set ALLOW_LESSON_35_GPU_JOB=yes after preflight}"
: "${IMAGE_REF:?Set IMAGE_REF to an immutable repository@sha256 digest}"
: "${STORAGE_CLASS:?Set the approved EBS CSI storage class}"
: "${GPU_INSTANCE_TYPE:?Set the existing GPU node instance type}"

if [[ "$ALLOW_LESSON_35_GPU_JOB" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_35_GPU_JOB must equal yes\n' >&2
  exit 1
fi

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
kubectl config current-context
kubectl auth can-i create jobs --namespace oms-l35
python3 scripts/render-k8s.py \
  --image "$IMAGE_REF" \
  --storage-class "$STORAGE_CLASS" \
  --instance-type "$GPU_INSTANCE_TYPE" \
  --output artifacts/training.yaml
kubectl apply -f artifacts/training.yaml
kubectl -n oms-l35 get pods -w
