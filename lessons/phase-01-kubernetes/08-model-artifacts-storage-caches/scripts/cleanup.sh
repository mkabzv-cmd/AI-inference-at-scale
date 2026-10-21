#!/usr/bin/env bash
set -euo pipefail

namespace=model-storage-lab
evidence_dir="${EVIDENCE_DIR:-artifacts}"
storage_evidence="${evidence_dir}/storage-before-cleanup.tsv"

mkdir -p "$evidence_dir"
: >"$storage_evidence"

printf 'Resources before cleanup:\n'
kubectl -n "$namespace" get all,pvc 2>/dev/null || true
kubectl get pv \
  -o custom-columns=NAME:.metadata.name,CLAIM:.spec.claimRef.name,RECLAIM:.spec.persistentVolumeReclaimPolicy \
  2>/dev/null || true

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  while IFS= read -r pvc; do
    [[ -n "$pvc" ]] || continue
    pv="$(
      kubectl -n "$namespace" get pvc "$pvc" \
        -o jsonpath='{.spec.volumeName}'
    )"
    handle=""
    if [[ -n "$pv" ]]; then
      handle="$(
        kubectl get pv "$pv" -o jsonpath='{.spec.csi.volumeHandle}'
      )"
    fi
    printf '%s\t%s\t%s\n' "$pvc" "$pv" "$handle" |
      tee -a "$storage_evidence"
  done < <(
    kubectl -n "$namespace" get pvc \
      -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
  )
fi

kubectl delete namespace "$namespace" --ignore-not-found --wait=true

pv_cleanup_failed=0
while IFS=$'\t' read -r _pvc pv _handle; do
  [[ -n "$pv" ]] || continue
  for _attempt in {1..30}; do
    if ! kubectl get pv "$pv" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  if kubectl get pv "$pv" >/dev/null 2>&1; then
    printf 'persistent volume still exists: %s\n' "$pv" >&2
    pv_cleanup_failed=1
  fi
done <"$storage_evidence"

if [[ "$pv_cleanup_failed" -ne 0 ]]; then
  printf '%s\n' \
    'Inspect reclaim policy, finalizers, and CSI events before continuing.' >&2
  exit 1
fi

kubectl delete storageclass model-cache-gp3 model-cache-gp3-auto \
  --ignore-not-found

printf 'Captured PVC, PV, and volume handles in %s\n' "$storage_evidence"
printf '%s\n' \
  'Kubernetes cleanup complete. Verify EBS volumes and GPU nodes in AWS.'
