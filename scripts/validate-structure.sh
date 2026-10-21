#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0
lesson_count=0

required_sections=(
  "Why this matters"
  "Learning outcomes"
  "Under the hood"
  "Lab outline"
  "Evidence to collect"
  "Completion gate"
  "Cleanup"
)

while IFS= read -r lesson_readme; do
  lesson_count=$((lesson_count + 1))
  for section in "${required_sections[@]}"; do
    if ! grep -Fq "## $section" "$lesson_readme"; then
      printf 'Missing section "%s": %s\n' "$section" "$lesson_readme" >&2
      failures=$((failures + 1))
    fi
  done
done < <(
  find "$repo_root/lessons" \
    -mindepth 3 \
    -maxdepth 3 \
    -name README.md \
    -print \
    | LC_ALL=C sort
)

if [[ "$lesson_count" -ne 50 ]]; then
  printf 'Expected 50 lesson READMEs, found %d\n' "$lesson_count" >&2
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  printf 'Validation failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

printf 'Validated the structure of %d lessons successfully\n' "$lesson_count"
