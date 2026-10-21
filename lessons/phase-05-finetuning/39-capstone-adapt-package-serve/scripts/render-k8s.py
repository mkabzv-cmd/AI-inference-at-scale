#!/usr/bin/env python3
"""Render private vLLM adapter serving resources with immutable inputs."""

import argparse
import re
from pathlib import Path


def dns_name(value, label):
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", value):
        raise SystemExit(f"{label} must be DNS-compatible")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--instance-type", required=True)
    parser.add_argument("--model-claim", required=True)
    parser.add_argument("--release-claim", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", args.image):
        raise SystemExit("image must be repository@sha256:<64 lowercase hex>")
    dns_name(args.instance_type, "instance type")
    dns_name(args.model_claim, "model claim")
    dns_name(args.release_claim, "release claim")
    lesson_root = Path(__file__).resolve().parent.parent
    text = (lesson_root / "k8s/serve-adapter.yaml.tpl").read_text()
    text = (
        text.replace("__IMAGE_REF__", args.image)
        .replace("__INSTANCE_TYPE__", args.instance_type)
        .replace("__MODEL_CLAIM__", args.model_claim)
        .replace("__RELEASE_CLAIM__", args.release_claim)
    )
    if "__" in text:
        raise SystemExit("unresolved template marker")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(args.output)


if __name__ == "__main__":
    main()
