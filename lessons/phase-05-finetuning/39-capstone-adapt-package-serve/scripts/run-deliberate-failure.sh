#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
test -f artifacts/fixture-release/release-manifest.json
python3 - <<'PY'
import json
from pathlib import Path

path = Path("artifacts/fixture-release/adapter/adapter_config.json")
value = json.loads(path.read_text())
value["r"] = 64
path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
PY
set +e
python3 src/verify_release.py \
  --release artifacts/fixture-release \
  --allow-fixture > artifacts/expected-tamper-failure.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: tampered adapter passed release verification\n' >&2
  exit 1
fi
grep -q 'artifact hash mismatch' artifacts/expected-tamper-failure.txt
printf 'PASS: adapter tampering invalidates the release manifest\n'
