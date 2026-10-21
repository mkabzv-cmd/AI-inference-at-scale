#!/usr/bin/env bash
set -euo pipefail

candidate="${1:?usage: $0 CANDIDATE_ID}"
if [[ ! "$candidate" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#candidate} > 63 )); then
  printf 'candidate ID must be a Kubernetes-safe name\n' >&2
  exit 2
fi
directory="artifacts/$candidate"
mkdir -p "$directory"
kubectl get all -n oms-lesson-23 -o wide > "$directory/kubernetes-all.txt"
kubectl get events -n oms-lesson-23 \
  --sort-by=.lastTimestamp > "$directory/events.txt"
kubectl logs -n oms-lesson-23 \
  "deployment/vllm" > "$directory/server.log"
kubectl describe pod -n oms-lesson-23 > "$directory/pods-describe.txt"
echo "review evidence for cluster/account identifiers before sharing"
