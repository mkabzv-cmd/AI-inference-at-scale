#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find "$repo_root/lessons" -mindepth 3 -maxdepth 3 -name README.md -print \
  | LC_ALL=C sort \
  | while IFS= read -r lesson_readme; do
      lesson_dir="$(basename "$(dirname "$lesson_readme")")"
      title="$(sed -n '1s/^# //p' "$lesson_readme")"
      status="$(
        sed -n 's/^\*\*Status:\*\*[[:space:]]*\([[:alnum:]-]*\).*/\1/p' \
          "$lesson_readme" \
          | head -n 1
      )"
      status="${status:-missing}"
      title="${title:-missing title}"
      printf '%-10s %-48s %s\n' "[$status]" "$lesson_dir" "$title"
    done \
  | awk '
      {
        print
        status = $1
        gsub(/^\[/, "", status)
        gsub(/\]$/, "", status)
        counts[status]++
        total++
      }
      END {
        printf "\nSummary:"
        order[1] = "draft"
        order[2] = "review"
        order[3] = "published"
        order[4] = "outline"
        order[5] = "refresh-needed"
        order[6] = "missing"
        separator = " "
        for (i = 1; i <= 6; i++) {
          status = order[i]
          if (counts[status] > 0) {
            printf "%s%d %s", separator, counts[status], status
            separator = ", "
          }
        }
        printf " (%d total)\n", total
      }
    '
