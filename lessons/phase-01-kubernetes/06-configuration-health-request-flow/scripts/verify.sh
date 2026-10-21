#!/usr/bin/env bash
set -euo pipefail

namespace="llm-health"
local_port="${LESSON_LOCAL_PORT:-18081}"
forward_log="$(mktemp)"
forward_pid=""

cleanup_forward() {
  if [[ -n "$forward_pid" ]]; then
    kill "$forward_pid" >/dev/null 2>&1 || true
    wait "$forward_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$forward_log"
}
trap cleanup_forward EXIT

kubectl rollout status deployment/health-app \
  -n "$namespace" --timeout=120s
kubectl wait --for=condition=Ready pod \
  -l app.kubernetes.io/name=health-app \
  -n "$namespace" --timeout=120s

ready_addresses="$(kubectl get endpointslice -n "$namespace" \
  -l kubernetes.io/service-name=health-app \
  -o jsonpath='{range .items[*].endpoints[?(@.conditions.ready==true)].addresses[*]}{.}{"\n"}{end}' \
  | sed '/^$/d' | wc -l | tr -d ' ')"

if [[ "$ready_addresses" != "1" ]]; then
  printf 'ERROR: expected 1 ready endpoint; got %s\n' "$ready_addresses" >&2
  exit 1
fi

kubectl port-forward -n "$namespace" service/health-app \
  "$local_port:80" >"$forward_log" 2>&1 &
forward_pid="$!"

root_response=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if root_response="$(curl --fail --silent --max-time 2 \
    "http://127.0.0.1:${local_port}/" 2>/dev/null)"; then
    break
  fi
  sleep 1
done

if [[ "$root_response" != *"hello from a ConfigMap"* ]]; then
  printf 'ERROR: root response did not contain ConfigMap greeting.\n' >&2
  cat "$forward_log" >&2
  exit 1
fi

config_response="$(curl --fail --silent --max-time 5 \
  "http://127.0.0.1:${local_port}/config")"
secret_response="$(curl --fail --silent --max-time 5 \
  "http://127.0.0.1:${local_port}/secret-fingerprint")"

if [[ "$config_response" != *"ConfigMap-backed volume"* ]]; then
  printf 'ERROR: mounted configuration was not readable.\n' >&2
  exit 1
fi

if [[ "$secret_response" != *'"token_exposed": false'* ]]; then
  printf 'ERROR: secret fingerprint endpoint failed.\n' >&2
  exit 1
fi

printf 'ready endpoints: %s\n' "$ready_addresses"
printf 'root response: %s\n' "$root_response"
printf 'mounted config response: %s\n' "$config_response"
printf 'secret handling response: %s\n' "$secret_response"
printf 'lesson 06 verification passed\n'
