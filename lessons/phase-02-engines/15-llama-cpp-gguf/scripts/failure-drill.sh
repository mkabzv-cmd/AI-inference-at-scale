#!/usr/bin/env bash
set -euo pipefail

name="qwen2.5-0.5b-instruct-q4_k_m.gguf"
source_file="artifacts/models/$name"
broken_file="artifacts/models/${name%.gguf}-corrupt.gguf"
test -f "$source_file" || { echo "download $name first" >&2; exit 1; }
cp "$source_file" "$broken_file"
printf 'corruption-drill' >>"$broken_file"
expected="$(
  python3 -c 'import json; d=json.load(open("config/artifacts.json")); print(next(x["sha256"] for x in d["files"] if x["name"]=="qwen2.5-0.5b-instruct-q4_k_m.gguf"))'
)"
set +e
EXPECTED_SHA256="$expected" BROKEN_FILE="$broken_file" python3 - <<'PY'
import hashlib
import os
from pathlib import Path
actual = hashlib.sha256(Path(os.environ["BROKEN_FILE"]).read_bytes()).hexdigest()
raise SystemExit(0 if actual == os.environ["EXPECTED_SHA256"] else 1)
PY
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  echo "corruption drill unexpectedly passed" >&2
  exit 1
fi
echo "checksum correctly rejected the corrupted copy"
rm "$broken_file"
