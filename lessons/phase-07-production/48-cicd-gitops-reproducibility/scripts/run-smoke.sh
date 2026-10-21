#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
release_path="${1:?Usage: run-smoke.sh RELEASE_JSON}"
port="${OMS_SMOKE_PORT:-8048}"
base_url="http://127.0.0.1:$port"

release_id="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release_id"])' \
    "$release_path"
)"
mkdir -p "$artifact_dir"
python3 "$lesson_dir/src/smoke_service.py" \
  --release "$release_path" \
  --port "$port" \
  >"$artifact_dir/smoke-server.log" 2>&1 &
server_pid=$!
cleanup() {
  if kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

ready=false
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    wait "$server_pid" 2>/dev/null || true
    printf 'Smoke service exited before readiness; inspect %s\n' \
      "$artifact_dir/smoke-server.log" >&2
    exit 1
  fi
  if curl -fs "$base_url/healthz" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 0.2
done
if [[ "$ready" != true ]]; then
  printf 'Smoke service did not become ready at %s\n' "$base_url" >&2
  exit 1
fi

python3 "$lesson_dir/src/smoke_check.py" \
  --base-url "$base_url" \
  --expected-release "$release_id"
