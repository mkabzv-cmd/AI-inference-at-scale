#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
for command in python3 curl; do
  command -v "$command" >/dev/null || {
    printf 'missing command: %s\n' "$command" >&2
    exit 1
  }
done
python3 -c 'import httpx, transformers; print("benchmark dependencies import")'
curl --fail --silent --show-error "$BENCH_BASE_URL/v1/models" >/dev/null
python3 -m json.tool schemas/result.schema.json >/dev/null
python3 - <<'PY'
import json
from pathlib import Path
for line in Path("bench/prompts.jsonl").read_text().splitlines():
    if line.strip():
        json.loads(line)
print("prompt JSONL parsed")
PY
printf 'preflight passed for %s\n' "$BENCH_BASE_URL"
