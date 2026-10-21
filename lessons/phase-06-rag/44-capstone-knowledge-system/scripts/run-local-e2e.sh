#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
port="${COURSE_PORT:-18080}"
mkdir -p "$lesson_dir/artifacts"

cleanup_server() {
  if [[ -n "${server_pid:-}" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup_server EXIT INT TERM

COURSE_HOST=127.0.0.1 \
COURSE_PORT="$port" \
COURSE_INDEX_DIR="$lesson_dir/artifacts/service-index" \
python3 "$lesson_dir/src/service.py" \
  >"$lesson_dir/artifacts/service.log" 2>&1 &
server_pid=$!

ready=0
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if python3 - "$port" <<'PY'
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
  echo "service did not become ready" >&2
  exit 1
fi

python3 "$lesson_dir/src/test_api.py" \
  --base-url "http://127.0.0.1:$port" \
  --output "$lesson_dir/artifacts/local-api-results.json"
