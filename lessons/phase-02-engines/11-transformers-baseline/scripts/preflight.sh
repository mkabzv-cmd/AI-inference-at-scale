#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l11}"
: "${MODEL_STORAGE_CLASS:?set MODEL_STORAGE_CLASS to an approved StorageClass}"
: "${GPU_NODE_SELECTOR_KEY:?set GPU_NODE_SELECTOR_KEY from an observed GPU node label}"
: "${GPU_NODE_SELECTOR_VALUE:?set GPU_NODE_SELECTOR_VALUE from an observed GPU node label}"

if [[ ! "$LAB_NAMESPACE" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#LAB_NAMESPACE} > 63 )); then
  echo "LAB_NAMESPACE must be a DNS label starting with open-models-" >&2
  exit 1
fi

for command in aws kubectl docker curl python3; do
  command -v "$command" >/dev/null || {
    printf 'missing required command: %s\n' "$command" >&2
    exit 1
  }
done

printf 'aws identity: '
aws sts get-caller-identity --query Arn --output text
printf 'kubernetes context: '
kubectl config current-context
kubectl cluster-info >/dev/null
kubectl auth can-i create namespaces | grep -qx yes
for resource in deployments.apps services persistentvolumeclaims; do
  kubectl auth can-i create "$resource" -n "$LAB_NAMESPACE" | grep -qx yes
done
kubectl get storageclass "$MODEL_STORAGE_CLASS" >/dev/null

selector="${GPU_NODE_SELECTOR_KEY}=${GPU_NODE_SELECTOR_VALUE}"
gpu_total="$(
  kubectl get nodes -l "$selector" -o json |
    python3 -c '
import json
import sys

total = 0
for node in json.load(sys.stdin).get("items", []):
    ready = any(
        item.get("type") == "Ready" and item.get("status") == "True"
        for item in node.get("status", {}).get("conditions", [])
    )
    if ready:
        total += int(
            node.get("status", {})
            .get("allocatable", {})
            .get("nvidia.com/gpu", "0")
        )
print(total)
'
)"
if [[ "$gpu_total" -lt 1 ]]; then
  echo "no selected Ready node advertises nvidia.com/gpu; stop before deploying" >&2
  exit 1
fi

if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
  echo "namespace already exists; inspect or clean it before a fresh run" >&2
  exit 1
fi

printf 'preflight passed: namespace=%s allocatable_gpus=%s\n' \
  "$LAB_NAMESPACE" "$gpu_total"
