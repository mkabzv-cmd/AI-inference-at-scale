#!/usr/bin/env bash
set -euo pipefail

: "${DOWNLOADER_IMAGE:?set DOWNLOADER_IMAGE to an image@sha256 reference}"
: "${MODEL_STORAGE_CLASS:?set MODEL_STORAGE_CLASS to the class you selected}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_eks_target
assert_namespace_owned_or_absent

if [[ ! "$DOWNLOADER_IMAGE" =~ ^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(\.cn)?/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$ ]]; then
  printf 'DOWNLOADER_IMAGE must be a complete private ECR image@sha256 reference\n' >&2
  exit 2
fi
case "$MODEL_STORAGE_CLASS" in
  model-cache-gp3 | model-cache-gp3-auto)
    assert_storageclass_owned_or_absent "$MODEL_STORAGE_CLASS"
    ;;
  *)
    printf 'MODEL_STORAGE_CLASS must be model-cache-gp3 or model-cache-gp3-auto\n' >&2
    exit 2
    ;;
esac

namespace=model-storage-lab
evidence_dir="${EVIDENCE_DIR:-artifacts}"
mkdir -p "$evidence_dir"

kubectl apply -f manifests/00-namespace.yaml

sed "s|REPLACE_STORAGE_CLASS|${MODEL_STORAGE_CLASS}|g" \
  manifests/02-model-cache-pvc.yaml |
  kubectl apply -f -

run_pod() {
  local output_name="$1"

  kubectl -n "$namespace" delete pod model-cache-pvc \
    --ignore-not-found --wait=true
  sed "s|REPLACE_DOWNLOADER_IMAGE|${DOWNLOADER_IMAGE}|g" \
    manifests/04-pvc-cache-pod.yaml |
    kubectl apply -f -

  kubectl -n "$namespace" wait \
    --for=condition=Initialized pod/model-cache-pvc \
    --timeout=20m
  kubectl -n "$namespace" logs model-cache-pvc -c populate-cache |
    tee "${evidence_dir}/${output_name}.log"
}

run_pod pvc-first-run
run_pod pvc-after-pod-replacement

kubectl -n "$namespace" get pod,pvc -o wide \
  >"${evidence_dir}/objects.txt"
kubectl -n "$namespace" get events \
  --sort-by=.metadata.creationTimestamp \
  >"${evidence_dir}/events.txt"

printf 'evidence written to %s\n' "$evidence_dir"
