#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required")
print("stdlib-only Python:", sys.version.split()[0])
PY
for file in cases/*.json configs/*.json results.schema.json; do
  python3 -m json.tool "$file" >/dev/null
done
echo "lesson 22 preflight passed"
