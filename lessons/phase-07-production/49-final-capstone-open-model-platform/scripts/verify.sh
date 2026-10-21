#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$lesson_dir/src/verify_capstone.py" "$@"
