#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l14}"
: "${MODEL_STORAGE_CLASS:?set MODEL_STORAGE_CLASS}"
: "${GPU_NODE_SELECTOR_KEY:?set GPU_NODE_SELECTOR_KEY}"
: "${GPU_NODE_SELECTOR_VALUE:?set GPU_NODE_SELECTOR_VALUE}"
for command in aws kubectl docker curl python3; do
  command -v "$command" >/dev/null || { echo "missing $command" >&2; exit 1; }
done
if [[ ! "$LAB_NAMESPACE" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#LAB_NAMESPACE} > 63 )); then
  echo "LAB_NAMESPACE must be a DNS label starting with open-models-" >&2
  exit 1
fi
aws sts get-caller-identity --query Arn --output text
kubectl config current-context
kubectl cluster-info >/dev/null
kubectl get storageclass "$MODEL_STORAGE_CLASS" >/dev/null
kubectl auth can-i create namespaces | grep -qx yes
for resource in deployments.apps services persistentvolumeclaims; do
  kubectl auth can-i create "$resource" -n "$LAB_NAMESPACE" | grep -qx yes
done
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
[[ "$gpu_total" -ge 1 ]] || {
  echo "no selected Ready node advertises nvidia.com/gpu" >&2
  exit 1
}
kubectl get nodes -l "$selector" \
  -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,GPU:.status.allocatable.nvidia\\.com/gpu
if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
  echo "namespace already exists" >&2
  exit 1
fi
test -f artifacts/image.env || { echo "run resolve-image.sh" >&2; exit 1; }
printf 'preflight passed; selected allocatable GPUs=%s; verify CUDA 13 driver compatibility\n' \
  "$gpu_total"
