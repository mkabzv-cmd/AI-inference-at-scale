#!/usr/bin/env python3
"""Normalize, template, mask, split, fingerprint, and audit chat JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable


EXPECTED_ROLES = ("system", "user", "assistant")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    return rows


def normalized_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("message content must be a string")
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        raise ValueError("message content must not be empty")
    return value


def canonicalize(
    row: dict[str, object],
    allowed_licenses: set[str],
) -> dict[str, object]:
    required = {"id", "source", "license", "messages"}
    if set(row) != required:
        raise ValueError(
            f"row fields must be exactly {sorted(required)}, got {sorted(row)}"
        )
    for field in ("id", "source", "license"):
        if not isinstance(row[field], str) or not str(row[field]).strip():
            raise ValueError(f"{field} must be a non-empty string")
    if row["license"] not in allowed_licenses:
        raise ValueError(
            f"{row['id']}: license {row['license']!r} is not allowlisted"
        )

    messages = row["messages"]
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError(f"{row['id']}: exactly three messages are required")

    normalized_messages = []
    for expected_role, message in zip(EXPECTED_ROLES, messages):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError(f"{row['id']}: invalid message object")
        if message["role"] != expected_role:
            raise ValueError(
                f"{row['id']}: expected role {expected_role}, "
                f"got {message['role']}"
            )
        normalized_messages.append(
            {
                "role": expected_role,
                "content": normalized_text(message["content"]),
            }
        )

    return {
        "id": row["id"].strip(),
        "source": row["source"].strip(),
        "license": row["license"].strip(),
        "messages": normalized_messages,
    }


def content_fingerprint(row: dict[str, object]) -> str:
    messages = row["messages"]
    serialized = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def split_for(identifier: str, seed: str, thresholds: dict[str, float]) -> str:
    digest = hashlib.sha256(f"{seed}:{identifier}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    if value < thresholds["train"]:
        return "train"
    if value < thresholds["validation"]:
        return "validation"
    return "test"


def append_segment(
    rendered: bytearray,
    labels: list[int],
    text: str,
    learn: bool,
) -> None:
    token_bytes = text.encode("utf-8")
    rendered.extend(token_bytes)
    labels.extend(token_bytes if learn else [-100] * len(token_bytes))


def render_and_mask(
    row: dict[str, object],
    template: dict[str, str],
    assistant_loss_only: bool,
) -> tuple[str, list[int], list[int]]:
    rendered = bytearray()
    labels: list[int] = []
    prefixes = {
        "system": template["system_prefix"],
        "user": template["user_prefix"],
        "assistant": template["assistant_prefix"],
    }
    for message in row["messages"]:
        role = str(message["role"])
        learn = role == "assistant" or not assistant_loss_only
        append_segment(rendered, labels, prefixes[role], False)
        append_segment(rendered, labels, str(message["content"]), learn)
        append_segment(rendered, labels, template["message_suffix"], learn)
    append_segment(
        rendered,
        labels,
        template["conversation_suffix"],
        not assistant_loss_only,
    )
    input_ids = list(rendered)
    return rendered.decode("utf-8"), input_ids, labels


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    allowed_licenses = set(config["allowed_licenses"])
    rows = [
        canonicalize(row, allowed_licenses)
        for row in read_jsonl(args.input)
    ]
    if not rows:
        raise SystemExit("dataset is empty")

    id_counts = Counter(str(row["id"]) for row in rows)
    duplicate_ids = sorted(
        identifier for identifier, count in id_counts.items() if count > 1
    )
    fingerprints = [content_fingerprint(row) for row in rows]
    fingerprint_counts = Counter(fingerprints)
    duplicate_content = sorted(
        fingerprint
        for fingerprint, count in fingerprint_counts.items()
        if count > 1
    )
    if duplicate_ids or duplicate_content:
        raise SystemExit(
            "duplicate audit failed: "
            f"ids={duplicate_ids}, content_hashes={duplicate_content}"
        )

    processed: dict[str, list[dict[str, object]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    for row, fingerprint in zip(rows, fingerprints):
        rendered, input_ids, labels = render_and_mask(
            row,
            config["template"],
            bool(config["assistant_loss_only"]),
        )
        if len(input_ids) > int(config["maximum_rendered_bytes"]):
            raise SystemExit(
                f"{row['id']}: rendered length {len(input_ids)} exceeds limit"
            )
        if not any(label != -100 for label in labels):
            raise SystemExit(f"{row['id']}: no supervised tokens remain")
        split = split_for(
            str(row["id"]),
            str(config["seed"]),
            config["split_thresholds"],
        )
        processed[split].append(
            {
                **row,
                "split": split,
                "content_sha256": fingerprint,
                "rendered_text": rendered,
                "input_ids": input_ids,
                "labels": labels,
                "token_count": len(input_ids),
                "supervised_token_count": sum(
                    label != -100 for label in labels
                ),
            }
        )

    empty_splits = [name for name, values in processed.items() if not values]
    if empty_splits:
        raise SystemExit(
            f"deterministic split produced empty split(s): {empty_splits}; "
            "add examples or choose a reviewed seed"
        )

    output_files = {}
    for split, split_rows in processed.items():
        output_path = args.output_dir / f"{split}.jsonl"
        write_jsonl(output_path, split_rows)
        output_files[split] = {
            "path": output_path.name,
            "rows": len(split_rows),
            "sha256": sha256_file(output_path),
            "tokens": sum(int(row["token_count"]) for row in split_rows),
            "supervised_tokens": sum(
                int(row["supervised_token_count"]) for row in split_rows
            ),
        }

    manifest = {
        "schema_version": 1,
        "dataset_name": config["dataset_name"],
        "dataset_version": config["dataset_version"],
        "input_path": args.input.name,
        "input_sha256": sha256_file(args.input),
        "config_sha256": sha256_file(args.config),
        "normalization": "Unicode NFKC plus whitespace collapse",
        "educational_tokenizer": "UTF-8 byte IDs; replace with target tokenizer",
        "assistant_loss_only": config["assistant_loss_only"],
        "files": output_files,
        "licenses": dict(Counter(str(row["license"]) for row in rows)),
        "sources": dict(Counter(str(row["source"]) for row in rows)),
        "duplicate_ids": [],
        "duplicate_content_hashes": [],
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output_files, sort_keys=True))
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
