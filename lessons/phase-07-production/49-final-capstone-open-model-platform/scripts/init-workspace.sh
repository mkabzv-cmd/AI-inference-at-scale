#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 ABSOLUTE_OR_RELATIVE_OUTPUT_DIRECTORY" >&2
  exit 2
fi

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$lesson_dir/src/init_workspace.py" --output "$1"
