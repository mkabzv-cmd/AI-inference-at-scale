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
done < <(find "$repo_root/lessons" -mindepth 3 -maxdepth 3 -name README.md -print | sort)

if [[ "$lesson_count" -ne 50 ]]; then
  printf 'Expected 50 lesson READMEs, found %d\n' "$lesson_count" >&2
  failures=$((failures + 1))
fi

if grep -RIEq \
  '(AKIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN (RSA|OPENSSH) PRIVATE KEY)' \
  "$repo_root" \
  --exclude-dir=.git \
  --exclude=validate-structure.sh; then
  printf 'Possible credential material detected\n' >&2
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  printf 'Validation failed with %d issue(s)\n' "$failures" >&2
  exit 1
fi

printf 'Validated %d lesson outlines successfully\n' "$lesson_count"
