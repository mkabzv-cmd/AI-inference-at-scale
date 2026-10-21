#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf 'Usage: %s SHORT_LABEL\n' "$0" >&2
  exit 2
fi

label="$1"
if [[ ! "$label" =~ ^[a-z0-9][a-z0-9-]{0,39}$ ]]; then
  printf 'Use lowercase letters, numbers, and hyphens (1-40 characters).\n' >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lesson_dir="$(cd "$script_dir/.." && pwd)"
repo_root="$(git -C "$lesson_dir" rev-parse --show-toplevel)"
experiment_id="$(date -u +%Y%m%dT%H%M%SZ)-${label}"
run_dir="$lesson_dir/runs/$experiment_id"

if [[ -e "$run_dir" ]]; then
  printf 'Refusing to overwrite: %s\n' "$run_dir" >&2
  exit 1
fi
mkdir -p "$run_dir"

git_commit="$(git -C "$repo_root" rev-parse HEAD)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  git_status="dirty"
else
  git_status="clean"
fi

python3 - "$run_dir/metadata.json" "$experiment_id" "$git_commit" "$git_status" <<'PY'
import json
import platform
import sys
from pathlib import Path

path, experiment_id, git_commit, git_status = sys.argv[1:]
record = {
    "schema_version": 1,
    "experiment_id": experiment_id,
    "code": {
        "git_commit": git_commit,
        "git_status": git_status,
        "command": "REPLACE_WITH_EXACT_COMMAND",
    },
    "software": {
        "python": platform.python_version(),
        "container_image_digest": None,
    },
    "model": {
        "repository": None,
        "revision": None,
        "tokenizer_revision": None,
    },
    "hardware": {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "gpu": None,
    },
    "workload": {
        "input": None,
        "seed": None,
        "parameters": {},
    },
    "results": {},
    "cleanup_verified": False,
}
Path(path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY

cat > "$run_dir/report.md" <<EOF
# Experiment $experiment_id

## Prediction

## Immutable inputs

- Git commit: \`$git_commit\`
- Worktree: \`$git_status\`
- Model/tokenizer revision:
- Container digest:

## Planned budget

- Nodes / GPUs per node / maximum minutes:
- Node-hours / GPU-hours:
- Cleanup command:

## Exact command

\`\`\`bash
REPLACE_ME
\`\`\`

## Measurements and explanation

## Failure and repair

## Cleanup evidence

- Namespace absent:
- GPU desired capacity zero:
- Load balancer absent:
- Storage retention decision:
EOF

printf 'Created %s\n' "${run_dir#"$lesson_dir/"}"
printf 'Next: edit %s\n' "${run_dir#"$lesson_dir/"}/report.md"
