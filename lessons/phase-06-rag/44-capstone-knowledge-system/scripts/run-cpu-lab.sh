#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$lesson_dir/scripts/run-local-e2e.sh"
"$lesson_dir/scripts/run-study.sh"
python3 "$lesson_dir/scripts/verify.py"
