#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find "$repo_root/lessons" -mindepth 3 -maxdepth 3 -name README.md -print \
  | sort \
  | while IFS= read -r lesson_readme; do
      lesson_dir="$(basename "$(dirname "$lesson_readme")")"
      title="$(sed -n '1s/^# //p' "$lesson_readme")"
      printf '%-48s %s\n' "$lesson_dir" "$title"
    done
