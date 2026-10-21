#!/usr/bin/env python3
"""Resolve and cache the exact model snapshot during an image build."""

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()
    snapshot_download(
        repo_id=args.repository,
        revision=args.revision,
        cache_dir=args.cache_dir,
    )


if __name__ == "__main__":
    main()
