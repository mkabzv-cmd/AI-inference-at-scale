#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null 2>&1 || {
  printf '[fail] python3 is required\n'
  exit 1
}
python3 - <<'PY'
import sys
if not ((3, 9) <= sys.version_info < (3, 13)):
    raise SystemExit("[fail] validated Python range is 3.9 through 3.12")
print("[ok] Python", ".".join(map(str, sys.version_info[:3])))
PY
if command -v nvidia-smi >/dev/null 2>&1; then
  printf '[info] nvidia-smi is installed; GPU lab is possible after PyTorch verification\n'
else
  printf '[info] nvidia-smi not found; use the complete CPU path\n'
fi
printf 'Lesson 02 preflight passed.\n'
