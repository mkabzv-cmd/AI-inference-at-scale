#!/usr/bin/env bash
set -euo pipefail

for name in python3 git; do
  command -v "$name" >/dev/null 2>&1 || {
    printf '[fail] required command not found: %s\n' "$name"
    exit 1
  }
done

python3 - <<'PY'
import ssl
import sys
if not (sys.version_info >= (3, 9) and sys.version_info < (3, 13)):
    raise SystemExit("[fail] validated Python range is 3.9 through 3.12")
print("[ok] Python", ".".join(map(str, sys.version_info[:3])))
print("[info] TLS library:", ssl.OPENSSL_VERSION)
if not ssl.OPENSSL_VERSION.startswith("OpenSSL "):
    print(
        "[warn] this Python is not linked to OpenSSL; "
        "use a current python.org/Homebrew interpreter if HTTPS packages warn"
    )
PY

printf '[ok] git: %s\n' "$(git --version)"
if [[ -x .venv/bin/python ]]; then
  printf '[ok] lesson virtual environment exists\n'
else
  printf '[info] create it with: python3 -m venv .venv\n'
fi
printf 'Lesson 01 preflight passed.\n'
