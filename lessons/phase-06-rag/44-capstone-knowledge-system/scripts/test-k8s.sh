#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${COURSE_NAMESPACE:?Set COURSE_NAMESPACE}"
local_port="${COURSE_LOCAL_PORT:-18080}"

cleanup_forward() {
  if [[ -n "${forward_pid:-}" ]]; then
    kill "$forward_pid" 2>/dev/null || true
    wait "$forward_pid" 2>/dev/null || true
  fi
}
trap cleanup_forward EXIT INT TERM

kubectl -n "$COURSE_NAMESPACE" port-forward \
  service/knowledge-service "$local_port:8080" \
  >"$lesson_dir/artifacts/port-forward.log" 2>&1 &
forward_pid=$!
ready=0
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if python3 - "$local_port" <<'PY'
import sys
import urllib.error
import urllib.request
try:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{sys.argv[1]}/readyz", timeout=1
    ) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except (OSError, urllib.error.URLError):
    raise SystemExit(1)
PY
  then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "port-forwarded service did not become ready" >&2
  exit 1
fi
python3 "$lesson_dir/src/test_api.py" \
  --base-url "http://127.0.0.1:$local_port" \
  --output "$lesson_dir/artifacts/k8s-api-results.json"
