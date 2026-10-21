#!/usr/bin/env bash
set -euo pipefail

node="${1:-}"
if [[ -z "$node" ]]; then
  printf 'Usage: %s NODE_NAME\n' "$0" >&2
  printf 'Choose a disposable worker from: kubectl get nodes\n' >&2
  exit 2
fi

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$context" ]]; then
  printf 'ERROR: kubectl has no current context.\n' >&2
  exit 1
fi
printf 'current context: %s\n' "$context"

if [[ "$context" != "kind-llm-scheduler-lab" &&
  "${ALLOW_NON_LAB_CONTEXT:-0}" != "1" ]]; then
  printf 'ERROR: expected context kind-llm-scheduler-lab; refusing %s.\n' \
    "$context" >&2
  printf '%s\n' \
    'For another verified disposable cluster, set ALLOW_NON_LAB_CONTEXT=1.' >&2
  exit 1
fi

kubectl get node "$node" >/dev/null

node_role="$(kubectl get node "$node" -o go-template='{{range $key, $value := .metadata.labels}}{{if eq $key "node-role.kubernetes.io/control-plane"}}control-plane{{end}}{{if eq $key "node-role.kubernetes.io/master"}}master{{end}}{{end}}')"
if [[ -n "$node_role" ]]; then
  printf 'ERROR: refusing to repurpose control-plane node %s.\n' "$node" >&2
  exit 1
fi

existing_label="$(kubectl get node "$node" \
  -o jsonpath='{.metadata.labels.lesson\.open-model-systems/accelerator}')"
if [[ -n "$existing_label" && "$existing_label" != "simulated-gpu" ]]; then
  printf 'ERROR: node %s already has a different course accelerator label: %s\n' \
    "$node" "$existing_label" >&2
  exit 1
fi

existing_taint="$(kubectl get node "$node" \
  -o jsonpath='{range .spec.taints[?(@.key=="nvidia.com/gpu")]}{.value}{":"}{.effect}{"\n"}{end}')"
if [[ -n "$existing_taint" && "$existing_taint" != "true:NoSchedule" ]]; then
  printf 'ERROR: node %s has an unexpected nvidia.com/gpu taint: %s\n' \
    "$node" "$existing_taint" >&2
  exit 1
fi
if [[ "$existing_taint" == "true:NoSchedule" &&
  "$existing_label" != "simulated-gpu" ]]; then
  printf 'ERROR: refusing to claim an existing GPU taint without the course '\
'marker on %s.\n' "$node" >&2
  exit 1
fi

kubectl label node "$node" \
  lesson.open-model-systems/accelerator=simulated-gpu --overwrite
kubectl taint node "$node" \
  nvidia.com/gpu=true:NoSchedule --overwrite

printf 'prepared simulated GPU node: %s\n' "$node"
kubectl get node "$node" --show-labels
kubectl describe node "$node" | sed -n '/Taints:/,/Unschedulable:/p'
