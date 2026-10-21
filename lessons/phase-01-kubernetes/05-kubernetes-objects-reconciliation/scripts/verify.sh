#!/usr/bin/env bash
set -euo pipefail

namespace="llm-systems"
deployment="hello-systems"
service="hello-systems"
local_port="${LESSON_LOCAL_PORT:-18080}"
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

kubectl get namespace "$namespace" >/dev/null
kubectl rollout status "deployment/$deployment" \
  -n "$namespace" --timeout=120s

desired="$(kubectl get deployment "$deployment" -n "$namespace" \
  -o jsonpath='{.spec.replicas}')"
updated="$(kubectl get deployment "$deployment" -n "$namespace" \
  -o jsonpath='{.status.updatedReplicas}')"
available="$(kubectl get deployment "$deployment" -n "$namespace" \
  -o jsonpath='{.status.availableReplicas}')"

if [[ "$desired" != "3" || "$updated" != "3" || "$available" != "3" ]]; then
  printf 'ERROR: expected desired/updated/available 3/3/3; got %s/%s/%s\n' \
    "$desired" "${updated:-0}" "${available:-0}" >&2
  exit 1
fi

selector_name="$(kubectl get service "$service" -n "$namespace" \
  -o jsonpath='{.spec.selector.app\.kubernetes\.io/name}')"
selector_component="$(kubectl get service "$service" -n "$namespace" \
  -o jsonpath='{.spec.selector.app\.kubernetes\.io/component}')"

if [[ "$selector_name" != "hello-systems" || "$selector_component" != "web" ]]; then
  printf 'ERROR: Service selector is broken: name=%s component=%s\n' \
    "$selector_name" "$selector_component" >&2
  exit 1
fi

ready_addresses="$(kubectl get endpointslice -n "$namespace" \
  -l kubernetes.io/service-name="$service" \
  -o jsonpath='{range .items[*].endpoints[?(@.conditions.ready==true)].addresses[*]}{.}{"\n"}{end}' \
  | sed '/^$/d' | wc -l | tr -d ' ')"

if [[ "$ready_addresses" != "3" ]]; then
  printf 'ERROR: expected 3 ready endpoint addresses; got %s\n' \
    "$ready_addresses" >&2
  exit 1
fi

kubectl port-forward -n "$namespace" "service/$service" \
  "$local_port:80" >"$forward_log" 2>&1 &
forward_pid="$!"

response=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if response="$(curl --fail --silent --max-time 2 \
    "http://127.0.0.1:${local_port}/hostname" 2>/dev/null)"; then
    break
  fi
  sleep 1
done

if [[ -z "$response" ]]; then
  printf 'ERROR: HTTP verification failed. Port-forward output:\n' >&2
  cat "$forward_log" >&2
  exit 1
fi

printf 'replicas: desired=%s updated=%s available=%s\n' \
  "$desired" "$updated" "$available"
printf 'ready endpoint addresses: %s\n' "$ready_addresses"
printf 'HTTP response hostname: %s\n' "$response"
printf 'lesson 05 verification passed\n'
