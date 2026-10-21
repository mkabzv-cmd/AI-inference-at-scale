#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
evidence_dir="${EVIDENCE_DIR:-artifacts}"
storage_evidence="${evidence_dir}/storage-before-cleanup.tsv"

mkdir -p "$evidence_dir"
: >"$storage_evidence"

printf 'Resources before cleanup:\n'
kubectl -n "$namespace" get all,pvc 2>/dev/null || true
kubectl -n "$namespace" get pvc \
  -o custom-columns=NAME:.metadata.name,PV:.spec.volumeName \
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

release_found="$(
  helm list --namespace "$namespace" --all \
    --filter "^${release}$" --short
)"
if [[ -n "$release_found" ]]; then
  helm uninstall "$release" \
    --namespace "$namespace" \
    --wait \
    --timeout 5m
else
  printf 'Helm release %s is already absent\n' "$release"
fi

remaining_pvcs="$(
  kubectl -n "$namespace" get pvc -o name 2>/dev/null || true
)"
if [[ -n "$remaining_pvcs" ]]; then
  printf '%s\n' \
    'PVCs remain after Helm uninstall; preserving the namespace for safety:' >&2
  printf '%s\n' "$remaining_pvcs" >&2
  printf '%s\n' \
    'This is expected for an existingClaim or helm.sh/resource-policy=keep.' >&2
  printf '%s\n' \
    'Decide explicitly whether to preserve or delete those data before continuing.' >&2
  exit 2
fi

kubectl delete namespace "$namespace" --ignore-not-found --wait=true

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'namespace still exists: %s\n' "$namespace" >&2
  exit 1
fi

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
    'Inspect reclaim policy, finalizers, and CSI events before scaling down.' >&2
  exit 1
fi

printf 'Kubernetes resources removed; captured storage IDs in %s\n' \
  "$storage_evidence"
printf '%s\n' \
  'Verify captured EBS volume IDs in AWS and return GPU nodes to baseline.'
