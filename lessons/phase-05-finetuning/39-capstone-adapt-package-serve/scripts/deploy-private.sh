#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_39_DEPLOY:?Set ALLOW_LESSON_39_DEPLOY=yes}"
: "${IMAGE_REF:?Set immutable vLLM image digest}"
: "${GPU_INSTANCE_TYPE:?Set existing GPU node instance type}"
: "${MODEL_CLAIM:?Set read-only PVC containing the exact base snapshot}"
: "${RELEASE_CLAIM:?Set read-only PVC containing the verified adapter release}"
if [[ "$ALLOW_LESSON_39_DEPLOY" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_39_DEPLOY must equal yes\n' >&2
  exit 1
fi
lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
kubectl config current-context
python3 scripts/render-k8s.py \
  --image "$IMAGE_REF" \
  --instance-type "$GPU_INSTANCE_TYPE" \
  --model-claim "$MODEL_CLAIM" \
  --release-claim "$RELEASE_CLAIM" \
  --output artifacts/serve-adapter.yaml
kubectl apply -f artifacts/serve-adapter.yaml
kubectl -n oms-l39 rollout status deployment/adapted-model --timeout=20m
kubectl -n oms-l39 port-forward service/adapted-model 8000:8000
