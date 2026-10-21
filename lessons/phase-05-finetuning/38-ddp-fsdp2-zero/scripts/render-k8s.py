#!/usr/bin/env python3
"""Render a three-node indexed Job with immutable inputs."""

import argparse
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--instance-type", required=True)
    parser.add_argument("--shared-claim", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", args.image):
        raise SystemExit("image must be repository@sha256:<64 lowercase hex>")
    if not re.fullmatch(
        r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", args.instance_type
    ):
        raise SystemExit("instance type must be a DNS-compatible value")
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", args.shared_claim):
        raise SystemExit("shared claim must be a DNS-compatible PVC name")
    lesson_root = Path(__file__).resolve().parent.parent
    text = (lesson_root / "k8s/three-node-training.yaml.tpl").read_text()
    text = (
        text.replace("__IMAGE_REF__", args.image)
        .replace("__INSTANCE_TYPE__", args.instance_type)
        .replace("__SHARED_CLAIM__", args.shared_claim)
    )
    if "__" in text:
        raise SystemExit("unresolved template marker")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(args.output)


if __name__ == "__main__":
    main()
