#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0
practical_count=0

required_sections=(
  "Why this matters"
  "Learning outcomes"
  "What you will build"
  "Files in this lesson"
  "Under the hood"
  "Prerequisites and preflight"
  "Cost and safety"
  "Predict before running"
  "Lab outline"
  "Step-by-step lab"
  "Deliberate failure"
  "Verification"
  "Troubleshooting"
  "Evidence to collect"
  "Exercises"
  "Completion gate"
  "Cleanup"
  "Primary references"
)

while IFS= read -r lesson_readme; do
  if ! grep -Eq \
    '^\*\*Status:\*\*[[:space:]]+(draft|review|published)([[:space:]]|$)' \
    "$lesson_readme"; then
    continue
  fi

  practical_count=$((practical_count + 1))
  lesson_dir="$(dirname "$lesson_readme")"

  for section in "${required_sections[@]}"; do
    if ! grep -Fq "## $section" "$lesson_readme"; then
      printf 'Practical lesson is missing section "%s": %s\n' \
        "$section" "$lesson_readme" >&2
      failures=$((failures + 1))
    fi
  done

  word_count="$(wc -w < "$lesson_readme" | tr -d ' ')"
  if [[ "$word_count" -lt 1000 ]]; then
    printf 'Practical lesson is too shallow (%s words, require 1000): %s\n' \
      "$word_count" "$lesson_readme" >&2
    failures=$((failures + 1))
  fi

  artifact_count="$(
    find "$lesson_dir" -type f \
      ! -name README.md \
      ! -path '*/artifacts/*' \
      | wc -l \
      | tr -d ' '
  )"
  if [[ "$artifact_count" -lt 1 ]]; then
    printf 'Practical lesson has no runnable/supporting files: %s\n' \
      "$lesson_dir" >&2
    failures=$((failures + 1))
  fi

  if grep -RIEq \
    --exclude-dir=artifacts \
    '(^|[^[:alpha:]])(TODO|TBD|FIXME)([^[:alpha:]]|$)' \
    "$lesson_dir"; then
    printf 'Practical lesson contains unresolved TODO/TBD/FIXME text: %s\n' \
      "$lesson_dir" >&2
    failures=$((failures + 1))
  fi
done < <(
  find "$repo_root/lessons" \
    -mindepth 3 \
    -maxdepth 3 \
    -name README.md \
    -print \
    | LC_ALL=C sort
)

if ! python3 - "$repo_root" <<'PY'
import collections
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
curriculum_path = root / "curriculum.yaml"
curriculum_lines = curriculum_path.read_text(encoding="utf-8").splitlines()

phase_pattern = re.compile(r"^\s{2}- id:\s*(phase-[a-z0-9-]+)\s*$")
lesson_pattern = re.compile(
    r'^\s{6}- \{\s*id:\s*"(?P<id>\d{2})",\s*'
    r"slug:\s*(?P<slug>[a-z0-9-]+),\s*"
    r"status:\s*(?P<status>[a-z-]+),\s*"
    r"compute:\s*\[[^\]]*\]\s*\}\s*$"
)
status_pattern = re.compile(
    r"^\*\*Status:\*\*\s+([a-z-]+)\s*$",
    flags=re.MULTILINE,
)
allowed_statuses = {
    "outline",
    "draft",
    "review",
    "published",
    "refresh-needed",
}

entries = []
failures = 0
current_phase = None
for line_number, line in enumerate(curriculum_lines, start=1):
    phase_match = phase_pattern.match(line)
    if phase_match:
        current_phase = phase_match.group(1)
        continue

    lesson_match = lesson_pattern.match(line)
    if lesson_match:
        if current_phase is None:
            print(
                f"Lesson appears before a phase at "
                f"{curriculum_path}:{line_number}",
                file=sys.stderr,
            )
            failures += 1
            continue
        entries.append(
            {
                "id": lesson_match.group("id"),
                "slug": lesson_match.group("slug"),
                "status": lesson_match.group("status"),
                "phase": current_phase,
            }
        )
    elif re.match(r'^\s*-\s*\{\s*id:\s*"\d{2}"', line):
        print(
            f"Unparseable lesson declaration at "
            f"{curriculum_path}:{line_number}",
            file=sys.stderr,
        )
        failures += 1

expected_ids = {f"{number:02d}" for number in range(50)}
declared_ids = [entry["id"] for entry in entries]
id_counts = collections.Counter(declared_ids)
duplicates = sorted(
    lesson_id for lesson_id, count in id_counts.items() if count > 1
)
if duplicates:
    print(
        "Duplicate lesson IDs in curriculum.yaml: " + ", ".join(duplicates),
        file=sys.stderr,
    )
    failures += 1

missing_ids = sorted(expected_ids - set(declared_ids))
extra_ids = sorted(set(declared_ids) - expected_ids)
if missing_ids:
    print(
        "Missing lesson IDs in curriculum.yaml: " + ", ".join(missing_ids),
        file=sys.stderr,
    )
    failures += 1
if extra_ids:
    print(
        "Unexpected lesson IDs in curriculum.yaml: " + ", ".join(extra_ids),
        file=sys.stderr,
    )
    failures += 1

readmes = sorted((root / "lessons").glob("phase-*/*/README.md"))
expected_paths = set()
status_counts = collections.Counter()

for entry in entries:
    lesson_id = entry["id"]
    expected_status = "draft" if int(lesson_id) <= 10 else "outline"
    if entry["status"] != expected_status:
        print(
            f"Current authored-slice policy requires lesson {lesson_id} to be "
            f"{expected_status}, not {entry['status']}",
            file=sys.stderr,
        )
        failures += 1

    if entry["status"] not in allowed_statuses:
        print(
            f"Unknown status for lesson {lesson_id}: {entry['status']}",
            file=sys.stderr,
        )
        failures += 1

    readme = (
        root
        / "lessons"
        / entry["phase"]
        / f"{lesson_id}-{entry['slug']}"
        / "README.md"
    )
    expected_paths.add(readme)
    if not readme.is_file():
        print(
            f"Declared lesson path does not exist: {readme}",
            file=sys.stderr,
        )
        failures += 1
        continue

    text = readme.read_text(encoding="utf-8")
    statuses = status_pattern.findall(text)
    if len(statuses) != 1:
        print(
            f"Expected exactly one Status line in {readme}, found "
            f"{len(statuses)}",
            file=sys.stderr,
        )
        failures += 1
        continue

    actual_status = statuses[0]
    status_counts[actual_status] += 1
    if actual_status != entry["status"]:
        print(
            f"Status mismatch for lesson {lesson_id}: "
            f"curriculum={entry['status']}, README={actual_status}",
            file=sys.stderr,
        )
        failures += 1

    first_line = text.splitlines()[0] if text.splitlines() else ""
    if not first_line.startswith(f"# {lesson_id} —"):
        print(
            f"Lesson title must start with '# {lesson_id} —': {readme}",
            file=sys.stderr,
        )
        failures += 1

actual_paths = set(readmes)
for unexpected in sorted(actual_paths - expected_paths):
    print(
        f"Lesson README is absent from curriculum.yaml: {unexpected}",
        file=sys.stderr,
    )
    failures += 1

if len(entries) != 50 or len(readmes) != 50:
    print(
        f"Expected 50 declarations and 50 lesson READMEs; found "
        f"{len(entries)} declarations and {len(readmes)} READMEs",
        file=sys.stderr,
    )
    failures += 1

if not failures:
    print(
        "Validated lesson metadata: "
        f"{status_counts['draft']} draft, "
        f"{status_counts['outline']} outline"
    )

raise SystemExit(1 if failures else 0)
PY
then
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  printf 'Practical-lesson validation failed with %d issue(s)\n' \
    "$failures" >&2
  exit 1
fi

printf 'Validated %d practical lesson draft(s)\n' "$practical_count"
