#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set VLLM_IMAGE to an immutable name@sha256 digest}"
: "${GPU_NODEGROUP:?set GPU_NODEGROUP to the approved lab GPU node group}"
candidate="${1:?usage: $0 CANDIDATE_ID}"
if [[ ! "$candidate" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#candidate} > 63 )); then
  printf 'candidate ID must be a Kubernetes-safe name\n' >&2
  exit 2
fi
mkdir -p artifacts
python3 src/render_manifest.py \
  --candidates configs/candidates.json \
  --candidate-id "$candidate" \
  --image "$VLLM_IMAGE" \
  --nodegroup "$GPU_NODEGROUP" \
  --output "artifacts/${candidate}.yaml"
kubectl apply --dry-run=client -f "artifacts/${candidate}.yaml" >/dev/null
echo "static client-side render accepted"
