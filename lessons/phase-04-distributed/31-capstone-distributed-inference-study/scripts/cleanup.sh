#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE to the exact remaining lesson namespace}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lesson_dir="$(cd "$script_dir/.." && pwd)"
common_dir="$(cd "$lesson_dir/../common/scripts" && pwd)"

(
  cd "$lesson_dir"
  "$common_dir/cleanup-namespace.sh"
  "$common_dir/scale-three-nodes.sh" down
)
printf '%s\n' \
  'Cleanup commands completed; perform the manual cloud/resource checks in README.'
