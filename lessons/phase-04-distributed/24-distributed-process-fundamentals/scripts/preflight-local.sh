#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null 2>&1 || {
  printf 'missing required command: python3\n' >&2
  exit 2
}

python3 - <<'PY'
import sys
if not ((3, 9) <= sys.version_info < (3, 13)):
    raise SystemExit("validated Python range is 3.9 through 3.12")
print("Python", sys.version.split()[0])
PY

if python3 -c 'import torch' >/dev/null 2>&1; then
  python3 - <<'PY'
import torch
import torch.distributed as dist
print("torch", torch.__version__)
print("distributed available", dist.is_available())
print("gloo available", dist.is_gloo_available())
if not dist.is_available() or not dist.is_gloo_available():
    raise SystemExit("this PyTorch build lacks required Gloo support")
PY
else
  printf '%s\n' \
    'PyTorch is not installed yet; create the venv and install requirements.'
fi
