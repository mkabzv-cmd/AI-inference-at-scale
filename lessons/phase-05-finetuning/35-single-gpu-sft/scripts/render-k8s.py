#!/usr/bin/env python3
"""Render the private single-GPU Job while enforcing immutable image input."""

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--storage-class", required=True)
    parser.add_argument("--instance-type", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", args.image):
        raise SystemExit("--image must be an immutable name@sha256:<64 hex> reference")
    if not re.fullmatch(
        r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", args.storage_class
    ):
        raise SystemExit("--storage-class must be a DNS-compatible name")
    if not re.fullmatch(
        r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", args.instance_type
    ):
        raise SystemExit("--instance-type must be a DNS-compatible value")
    lesson_root = Path(__file__).resolve().parent.parent
    template = (lesson_root / "k8s/training.yaml.tpl").read_text()
    rendered = (
        template.replace("__IMAGE_REF__", args.image)
        .replace("__STORAGE_CLASS__", args.storage_class)
        .replace("__INSTANCE_TYPE__", args.instance_type)
    )
    if "__" in rendered:
        raise SystemExit("unresolved template marker")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(args.output)


if __name__ == "__main__":
    main()
