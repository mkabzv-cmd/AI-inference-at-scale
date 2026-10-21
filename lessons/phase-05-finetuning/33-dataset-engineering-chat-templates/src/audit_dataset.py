#!/usr/bin/env python3
"""Audit processed split separation, masks, hashes, and manifest counts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def rows(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    seen_ids: set[str] = set()
    seen_content: set[str] = set()

    for split in ("train", "validation", "test"):
        path = args.dataset_dir / f"{split}.jsonl"
        split_rows = rows(path)
        expected = manifest["files"][split]
        if sha256_file(path) != expected["sha256"]:
            failures.append(f"{split}: sha256 differs from manifest")
        if len(split_rows) != expected["rows"]:
            failures.append(f"{split}: row count differs from manifest")

        for row in split_rows:
            identifier = str(row["id"])
            fingerprint = str(row["content_sha256"])
            if identifier in seen_ids:
                failures.append(f"{identifier}: appears across splits")
            if fingerprint in seen_content:
                failures.append(f"{identifier}: content appears across splits")
            seen_ids.add(identifier)
            seen_content.add(fingerprint)

            if row["split"] != split:
                failures.append(f"{identifier}: embedded split is incorrect")
            input_ids = row["input_ids"]
            labels = row["labels"]
            if len(input_ids) != len(labels):
                failures.append(f"{identifier}: input/label length mismatch")
            supervised = [label for label in labels if label != -100]
            if len(supervised) != row["supervised_token_count"]:
                failures.append(f"{identifier}: supervised count mismatch")
            if not supervised:
                failures.append(f"{identifier}: no supervised bytes")
            first_supervised = next(
                (
                    index
                    for index, label in enumerate(labels)
                    if label != -100
                ),
                None,
            )
            assistant_offset = row["rendered_text"].encode("utf-8").find(
                b"<|assistant|>\n"
            ) + len(b"<|assistant|>\n")
            if first_supervised != assistant_offset:
                failures.append(
                    f"{identifier}: mask does not begin at assistant content"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        f"PASS: {len(seen_ids)} unique examples; deterministic splits, "
        "hashes, and assistant-only masks verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
