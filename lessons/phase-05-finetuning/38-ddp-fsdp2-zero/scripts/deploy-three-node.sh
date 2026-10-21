#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_38_GPU_JOB:?Set ALLOW_LESSON_38_GPU_JOB=yes}"
: "${IMAGE_REF:?Set an immutable training image digest}"
: "${GPU_INSTANCE_TYPE:?Set the existing G-series node instance type}"
: "${SHARED_CLAIM:?Set an approved existing ReadWriteMany PVC name}"
if [[ "$ALLOW_LESSON_38_GPU_JOB" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_38_GPU_JOB must equal yes\n' >&2
  exit 1
fi

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
kubectl config current-context
kubectl auth can-i create jobs --namespace oms-l38
python3 scripts/render-k8s.py \
  --image "$IMAGE_REF" \
  --instance-type "$GPU_INSTANCE_TYPE" \
  --shared-claim "$SHARED_CLAIM" \
  --output artifacts/three-node-training.yaml
kubectl apply -f artifacts/three-node-training.yaml
kubectl -n oms-l38 wait \
  --for=condition=complete \
  job/trainer \
  --timeout=30m
