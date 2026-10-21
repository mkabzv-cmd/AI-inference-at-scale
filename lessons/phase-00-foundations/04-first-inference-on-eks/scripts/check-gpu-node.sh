#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"
: "${GPU_NODEGROUP_NAME:?Set GPU_NODEGROUP_NAME}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_kube_context_matches_cluster

node_json="$(
  kubectl get nodes \
    -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
    -o json
)"

python3 -c '
import json, sys
data = json.load(sys.stdin)
ready_nodes = 0
single_gpu_nodes = 0
for node in data["items"]:
    metadata = node["metadata"]
    status = node["status"]
    conditions = {c["type"]: c["status"] for c in status.get("conditions", [])}
    allocatable = status.get("allocatable", {})
    capacity = status.get("capacity", {})
    ready = conditions.get("Ready")
    gpu = int(allocatable.get("nvidia.com/gpu", "0"))
    print("node:", metadata["name"])
    print("ready:", ready)
    print("instance type:", metadata.get("labels", {}).get("node.kubernetes.io/instance-type"))
    print("capacity nvidia.com/gpu:", capacity.get("nvidia.com/gpu", "0"))
    print("allocatable nvidia.com/gpu:", gpu)
    if ready == "True":
        ready_nodes += 1
        if gpu == 1:
            single_gpu_nodes += 1
if ready_nodes != 1:
    raise SystemExit(
        f"[fail] lesson 04 requires exactly one Ready selected node; found {ready_nodes}"
    )
if single_gpu_nodes != 1:
    raise SystemExit(
        "[fail] lesson 04 requires that node to advertise exactly one allocatable GPU"
    )
print("[ok] exactly one Ready node advertises exactly one allocatable NVIDIA GPU")
' <<< "$node_json"
