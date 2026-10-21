#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
port="${OMS_PORT:-8045}"
base_url="http://127.0.0.1:$port"
pid_file="$artifact_dir/server.pid"

mkdir -p "$artifact_dir"
: >"$artifact_dir/server.ndjson"
rm -f -- "$pid_file"

python3 "$lesson_dir/src/fake_model_server.py" \
  --port "$port" \
  --capacity 2 \
  --log-path "$artifact_dir/server.ndjson" \
  >"$artifact_dir/server.stdout.log" 2>&1 &
server_pid=$!
printf '%s\n' "$server_pid" >"$pid_file"

cleanup() {
  if kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  rm -f -- "$pid_file"
}
trap cleanup EXIT

ready=false
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    wait "$server_pid" 2>/dev/null || true
    printf 'Local server exited before readiness; inspect %s\n' \
      "$artifact_dir/server.stdout.log" >&2
    exit 1
  fi
  if curl -fs "$base_url/readyz" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 0.2
done
if [[ "$ready" != true ]]; then
  printf 'Local server did not become ready at %s\n' "$base_url" >&2
  exit 1
fi

python3 "$lesson_dir/src/load_generator.py" \
  --base-url "$base_url" \
  --plan "$lesson_dir/configs/load-plan.json" \
  --output "$artifact_dir/requests.ndjson"

curl -fsS "$base_url/metrics" >"$artifact_dir/metrics.prom"

python3 "$lesson_dir/src/analyze_capacity.py" \
  --records "$artifact_dir/requests.ndjson" \
  --metadata "$artifact_dir/requests.metadata.json" \
  --plan "$lesson_dir/configs/load-plan.json" \
  --output "$artifact_dir/capacity-report.json"

python3 "$lesson_dir/scripts/verify.py" \
  --records "$artifact_dir/requests.ndjson" \
  --server-log "$artifact_dir/server.ndjson" \
  --report "$artifact_dir/capacity-report.json"

printf 'Evidence written under %s\n' "$artifact_dir"
