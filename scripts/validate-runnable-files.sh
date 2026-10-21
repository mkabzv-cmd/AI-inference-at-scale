#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0

while IFS= read -r script; do
  if ! bash -n "$script"; then
    failures=$((failures + 1))
  fi
  if [[ ! -x "$script" ]]; then
    printf 'Shell script is not executable: %s\n' "$script" >&2
    failures=$((failures + 1))
  fi
done < <(
  find "$repo_root/lessons" "$repo_root/scripts" \
    -type d \
    \( \
      -name .git \
      -o -name .venv \
      -o -name artifacts \
      -o -name __pycache__ \
    \) \
    -prune \
    -o -type f \
    -name '*.sh' \
    -print \
    | LC_ALL=C sort
)

if ! python3 - "$repo_root" <<'PY'
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

root = Path(sys.argv[1]).resolve()
failures = 0


def repository_files():
    """Return tracked and non-ignored untracked files, with a tarball fallback."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        ignored_directories = {
            ".git",
            ".venv",
            "artifacts",
            "__pycache__",
            "node_modules",
        }
        return sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and not ignored_directories.intersection(path.relative_to(root).parts)
        )

    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = root / os.fsdecode(raw_path)
        if path.is_file() and not path.is_symlink():
            paths.append(path)
    return sorted(paths)


def prose_without_code_or_comments(text):
    """Remove fenced/inline code and comments before discovering Markdown links."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    output = []
    fence_character = None
    fence_length = 0

    for line in text.splitlines():
        fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue

        # Inline code may contain documentation examples that look like links.
        line = re.sub(r"(`+)(.*?)\1", "", line)
        output.append(line)

    return "\n".join(output)


def inline_link_targets(text):
    """Yield balanced inline Markdown link/image destinations."""
    index = 0
    while True:
        opener = text.find("](", index)
        if opener < 0:
            return
        if text.rfind("[", index, opener) < 0:
            index = opener + 2
            continue

        cursor = opener + 2
        depth = 1
        escaped = False
        while cursor < len(text):
            character = text[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1

        if depth != 0:
            return

        content = text[opener + 2 : cursor].strip()
        if content.startswith("<"):
            closing = content.find(">")
            target = content[1:closing] if closing >= 0 else content[1:]
        else:
            target_characters = []
            nested_depth = 0
            escaped = False
            for character in content:
                if escaped:
                    target_characters.append(character)
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == "(":
                    nested_depth += 1
                    target_characters.append(character)
                elif character == ")":
                    nested_depth = max(0, nested_depth - 1)
                    target_characters.append(character)
                elif character.isspace() and nested_depth == 0:
                    break
                else:
                    target_characters.append(character)
            target = "".join(target_characters)

        if target:
            yield target
        index = cursor + 1


files = repository_files()

for path in (candidate for candidate in files if candidate.suffix == ".py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as error:
        print(f"Invalid Python source: {path}: {error}", file=sys.stderr)
        failures += 1

for path in (candidate for candidate in files if candidate.suffix == ".json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"Invalid JSON: {path}: {error}", file=sys.stderr)
        failures += 1

for path in (candidate for candidate in files if candidate.suffix == ".md"):
    try:
        text = prose_without_code_or_comments(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        print(f"Invalid UTF-8 Markdown: {path}: {error}", file=sys.stderr)
        failures += 1
        continue

    for raw_target in inline_link_targets(text):
        target = raw_target.strip()
        if (
            not target
            or target.startswith("#")
            or target.startswith("/")
            or target.startswith("//")
        ):
            continue

        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            continue

        target_path = unquote(parsed.path)
        if not target_path:
            continue

        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            print(
                f"Relative Markdown link escapes the repository in "
                f"{path.relative_to(root)}: {raw_target}",
                file=sys.stderr,
            )
            failures += 1
            continue

        if not resolved.exists():
            print(
                f"Broken relative Markdown link in "
                f"{path.relative_to(root)}: {raw_target}",
                file=sys.stderr,
            )
            failures += 1

raise SystemExit(1 if failures else 0)
PY
then
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  printf 'Runnable-file validation failed with %d issue(s)\n' \
    "$failures" >&2
  exit 1
fi

printf '%s\n' \
  'Validated shell/Python syntax, JSON, relative links, and script permissions'
