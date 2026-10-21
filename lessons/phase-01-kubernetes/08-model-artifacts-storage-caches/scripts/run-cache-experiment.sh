#!/usr/bin/env bash
set -euo pipefail

: "${DOWNLOADER_IMAGE:?set DOWNLOADER_IMAGE to an image@sha256 reference}"
: "${MODEL_STORAGE_CLASS:?set MODEL_STORAGE_CLASS to the class you selected}"

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
