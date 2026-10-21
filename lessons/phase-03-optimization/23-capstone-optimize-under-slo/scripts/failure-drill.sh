#!/usr/bin/env bash
set -euo pipefail

action="${1:-break}"
case "$action" in
  break)
    kubectl patch service vllm -n oms-lesson-23 \
      --type merge \
      -p '{"spec":{"selector":{"app.kubernetes.io/name":"does-not-exist"}}}'
    echo "service selector broken; endpoints should become empty"
    ;;
  repair)
    kubectl patch service vllm -n oms-lesson-23 \
      --type merge \
      -p '{"spec":{"selector":{"app.kubernetes.io/name":"vllm"}}}'
    echo "service selector repaired"
    ;;
  *)
    echo "usage: $0 break|repair" >&2
    exit 2
    ;;
esac
kubectl get service,endpoints -n oms-lesson-23
