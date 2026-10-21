#!/usr/bin/env python3
"""Render the Kubernetes template only with a digest-pinned image."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

IMAGE = re.compile(r"^[a-zA-Z0-9._:/-]+@sha256:[a-f0-9]{64}$")
NAMESPACE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
UNRESOLVED = re.compile(r"__[A-Z0-9_]+__")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not IMAGE.fullmatch(args.image):
        raise SystemExit("image must be an immutable repository@sha256:<64 hex> reference")
    if len(args.namespace) > 63 or not NAMESPACE.fullmatch(args.namespace):
        raise SystemExit("namespace is not a valid DNS label")
    rendered = (
        args.template.read_text()
        .replace("__IMAGE_REF__", args.image)
        .replace("__NAMESPACE__", args.namespace)
    )
    unresolved = sorted(set(UNRESOLVED.findall(rendered)))
    if unresolved:
        raise SystemExit(
            "template contains unresolved tokens: " + ", ".join(unresolved)
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"rendered digest-pinned manifest to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
