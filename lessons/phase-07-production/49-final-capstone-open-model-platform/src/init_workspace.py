#!/usr/bin/env python3
"""Initialize a capstone evidence workspace without overwriting any file."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lesson_dir = Path(__file__).resolve().parents[1]
    template_dir = lesson_dir / "templates"
    output = args.output.expanduser().resolve()
    if output == Path("/") or output == Path.home():
        raise SystemExit("refusing to initialize at a broad filesystem root")
    if output.exists() and not output.is_dir():
        raise SystemExit(f"output exists and is not a directory: {output}")
    if output.exists() and any(output.iterdir()):
        raise SystemExit(
            f"output is not empty; no files were changed: {output}"
        )
    output.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for source in sorted(template_dir.rglob("*")):
        if not source.is_file():
            continue
        rel = source.relative_to(template_dir)
        destination = output / rel
        if destination.exists():
            raise SystemExit(f"refusing to overwrite: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(rel.as_posix())

    print(f"initialized={output}")
    print(f"files={len(copied)}")
    print("state=incomplete")
    print("next=replace every __...__ marker, collect observed evidence, then finalize")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
