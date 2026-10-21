#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required")
print("python:", sys.version.split()[0])
PY
for file in configs/*.json fixtures/*.json results.schema.json; do
  python3 -m json.tool "$file" >/dev/null
done

if [[ "${RUN_GPU_TRACK:-0}" == "1" ]]; then
  : "${CONFIRM_LAB_CONTEXT:?set CONFIRM_LAB_CONTEXT to the exact kubectl context}"
  : "${GPU_NODEGROUP:?set GPU_NODEGROUP to the approved lab GPU node group}"
  : "${CONFIRM_GPU_NODEGROUP:?repeat the exact GPU_NODEGROUP value}"
  if [[ ! "$GPU_NODEGROUP" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$ ]]; then
    echo "GPU_NODEGROUP is not a Kubernetes label value" >&2
    exit 2
  fi
  [[ "$CONFIRM_GPU_NODEGROUP" == "$GPU_NODEGROUP" ]] || {
    echo "CONFIRM_GPU_NODEGROUP must exactly match GPU_NODEGROUP" >&2
    exit 2
  }
  command -v kubectl >/dev/null
  command -v aws >/dev/null
  command -v docker >/dev/null
  context="$(kubectl config current-context)"
  [[ "$context" == "$CONFIRM_LAB_CONTEXT" ]] || {
    echo "context mismatch: current=$context confirmed=$CONFIRM_LAB_CONTEXT" >&2
    exit 2
  }
  aws sts get-caller-identity
  kubectl auth can-i create namespaces | grep -qx yes
  for resource in deployments.apps services; do
    kubectl auth can-i create "$resource" \
      --namespace oms-lesson-23 | grep -qx yes
  done
  gpu_total="$(
    kubectl get nodes \
      -l "eks.amazonaws.com/nodegroup=${GPU_NODEGROUP}" \
      -o json |
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
    echo "no Ready node in the selected group advertises an NVIDIA GPU" >&2
    exit 1
  }
  printf 'Selected-group Ready allocatable GPUs: %s\n' "$gpu_total"
fi
echo "lesson 23 preflight passed"
