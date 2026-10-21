#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-eks-target.sh"

evidence_dir="${EVIDENCE_DIR:-artifacts}"
mkdir -p "$evidence_dir"

kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=${GPU_NODEGROUP}" \
  -o json >"$evidence_dir/nodes.json"
python3 "$script_dir/verify-three-gpu-nodes.py" \
  --nodegroup "$GPU_NODEGROUP" \
  <"$evidence_dir/nodes.json" \
  | tee "$evidence_dir/node-verification.json"

kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=${GPU_NODEGROUP}" \
  -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,INTERNAL_IP:.status.addresses[?(@.type=="InternalIP")].address,GPU:.status.allocatable.nvidia\.com/gpu' \
  >"$evidence_dir/node-topology.txt"

: >"$evidence_dir/pods-on-selected-nodes.txt"
while IFS= read -r node_name; do
  [[ -n "$node_name" ]] || continue
  printf '## node %s\n' "$node_name" \
    >>"$evidence_dir/pods-on-selected-nodes.txt"
  kubectl get pods --all-namespaces \
    --field-selector "spec.nodeName=${node_name}" \
    -o wide >>"$evidence_dir/pods-on-selected-nodes.txt"
  printf '\n' >>"$evidence_dir/pods-on-selected-nodes.txt"
done < <(
  kubectl get nodes \
    -l "eks.amazonaws.com/nodegroup=${GPU_NODEGROUP}" \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
)
printf '%s\n' \
  "Selected-node topology captured under $evidence_dir; sanitize names/IPs before sharing."
