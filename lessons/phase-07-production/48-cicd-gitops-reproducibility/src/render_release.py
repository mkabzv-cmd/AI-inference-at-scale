#!/usr/bin/env python3
"""Render GitOps workload from the immutable release contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_release import validate_release


NAMESPACE = re.compile(
    r"^oms-lesson-48-[a-z0-9](?:[-a-z0-9]{0,45}[a-z0-9])?$"
)
TOKEN = re.compile(r"__[A-Z][A-Z0-9_]+__")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not NAMESPACE.fullmatch(args.namespace):
        raise SystemExit("namespace must be a DNS-safe oms-lesson-48-* name")
    release = json.loads(args.release.read_text(encoding="utf-8"))
    failures = validate_release(release)
    if failures:
        raise SystemExit("release validation failed: " + "; ".join(failures))
    image = str(release["image"])
    rendered = (
        args.template.read_text(encoding="utf-8")
        .replace("__NAMESPACE__", args.namespace)
        .replace("__IMAGE__", image)
        .replace("__RELEASE_ID__", str(release["release_id"]))
        .replace("__MODEL_REVISION__", str(release["model"]["revision"]))
        .replace("__INDEX_VERSION__", str(release["index"]["version"]))
    )
    if TOKEN.search(rendered):
        raise SystemExit("unresolved template marker remains")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"rendered={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
