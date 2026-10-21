#!/usr/bin/env bash
set -euo pipefail

failures=0

require_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf '[ok] %s: %s\n' "$name" "$("$name" --version 2>&1 | head -n 1)"
  else
    printf '[fail] %s: not found\n' "$name"
    failures=$((failures + 1))
  fi
}

optional_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf '[info] %s: installed\n' "$name"
  else
    printf '[info] %s: not found (optional in lesson 00)\n' "$name"
  fi
}

if (( BASH_VERSINFO[0] >= 3 )); then
  printf '[ok] bash: %s\n' "$BASH_VERSION"
else
  printf '[fail] bash 3.2 or newer is required\n'
  failures=$((failures + 1))
fi

require_command python3
require_command git
optional_command docker
optional_command kubectl
optional_command aws

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  printf '[ok] repository worktree detected\n'
else
  printf '[fail] run inside the cloned Git repository\n'
  failures=$((failures + 1))
fi

python_version_ok="$(
  python3 -c 'import sys; print(int(sys.version_info >= (3, 9)))' 2>/dev/null || printf 0
)"
if [[ "$python_version_ok" != "1" ]]; then
  printf '[fail] Python 3.9 or newer is required\n'
  failures=$((failures + 1))
fi

if (( failures > 0 )); then
  printf 'Preflight failed with %d problem(s).\n' "$failures"
  exit 1
fi
printf 'Preflight passed for lesson 00.\n'
