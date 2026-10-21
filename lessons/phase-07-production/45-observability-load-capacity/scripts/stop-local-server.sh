#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
pid_file="$artifact_dir/server.pid"

if [[ ! -f "$pid_file" ]]; then
  printf 'No server PID file exists\n'
  exit 0
fi

server_pid="$(cat "$pid_file")"
if [[ "$server_pid" =~ ^[0-9]+$ ]] && kill -0 "$server_pid" 2>/dev/null; then
  kill "$server_pid"
fi
rm -f -- "$pid_file"
printf 'Local server stopped\n'
