#!/usr/bin/env python3
"""Validate, normalize, chunk, embed, and manifest a small RAG corpus."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]+$")
TOKEN = re.compile(r"[a-z0-9]+")
SENTENCE = re.compile(r"[^.!?]+(?:[.!?]+|$)")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def normalize_text(value: str) -> str:
    """Return stable text; offsets in emitted chunks refer to this representation."""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", normalized).strip()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: record must be an object")
        value["_source_line"] = line_number
        records.append(value)
    return records


def validate_config(config: dict[str, Any]) -> None:
    errors: list[str] = []
    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    licenses = config.get("allowed_licenses")
    if (
        not isinstance(licenses, list)
        or not licenses
        or not all(isinstance(item, str) and item for item in licenses)
        or len(set(licenses)) != len(licenses)
    ):
        errors.append("allowed_licenses must be a non-empty unique string list")
    chunking = config.get("chunking", {})
    target_words = chunking.get("target_words")
    overlap_sentences = chunking.get("overlap_sentences")
    if not isinstance(target_words, int) or not 1 <= target_words <= 100_000:
        errors.append("chunking.target_words must be between 1 and 100000")
    if (
        not isinstance(overlap_sentences, int)
        or not 0 <= overlap_sentences <= 1000
    ):
        errors.append("chunking.overlap_sentences must be between 0 and 1000")
    embedding = config.get("embedding", {})
    if embedding.get("algorithm") != "signed-word-and-character-hash":
        errors.append(
            "embedding.algorithm must be signed-word-and-character-hash"
        )
    dimensions = embedding.get("dimensions")
    if not isinstance(dimensions, int) or not 1 <= dimensions <= 65_536:
        errors.append("embedding.dimensions must be between 1 and 65536")
    if embedding.get("l2_normalize") is not True:
        errors.append("embedding.l2_normalize must be true")
    approximate = config.get("approximate_index", {})
    hyperplanes = approximate.get("hyperplanes")
    max_distance = approximate.get("max_hamming_distance")
    if not isinstance(hyperplanes, int) or not 1 <= hyperplanes <= 64:
        errors.append("approximate_index.hyperplanes must be between 1 and 64")
    if (
        not isinstance(max_distance, int)
        or not isinstance(hyperplanes, int)
        or not 0 <= max_distance <= hyperplanes
    ):
        errors.append(
            "approximate_index.max_hamming_distance must be between 0 and hyperplanes"
        )
    if errors:
        raise ValueError(
            "invalid ingestion configuration:\n- " + "\n- ".join(errors)
        )


def validate_documents(
    documents: list[dict[str, Any]], allowed_licenses: set[str]
) -> None:
    errors: list[str] = []
    identities: set[tuple[str, str]] = set()
    required = {
        "document_id",
        "version",
        "title",
        "source_uri",
        "license",
        "tenant_ids",
        "published_at",
        "sections",
    }
    for document in documents:
        line = document.get("_source_line", "?")
        supplied = set(document) - {"_source_line"}
        missing = sorted(required - supplied)
        unknown = sorted(supplied - required)
        if missing:
            errors.append(f"line {line}: missing fields {missing}")
            continue
        if unknown:
            errors.append(f"line {line}: unknown fields {unknown}")
        document_id = document["document_id"]
        if not isinstance(document_id, str) or not IDENTIFIER.fullmatch(
            document_id
        ):
            errors.append(
                f"line {line}: document_id must be a lowercase DNS-like identifier"
            )
        identity = (str(document["document_id"]), str(document["version"]))
        if identity in identities:
            errors.append(f"line {line}: duplicate identity {identity[0]}@{identity[1]}")
        identities.add(identity)
        if not isinstance(document["version"], str) or not SEMVER.fullmatch(
            document["version"]
        ):
            errors.append(f"line {line}: version must be numeric semantic version")
        if not isinstance(document["title"], str) or not normalize_text(
            document["title"]
        ):
            errors.append(f"line {line}: title must be a non-empty string")
        if not isinstance(document["source_uri"], str) or not document[
            "source_uri"
        ].strip():
            errors.append(f"line {line}: source_uri must be a non-empty string")
        if not isinstance(document["license"], str):
            errors.append(f"line {line}: license must be a string")
        elif document["license"] not in allowed_licenses:
            errors.append(
                f"line {line}: license {document['license']!r} is not in the allowlist"
            )
        tenants = document["tenant_ids"]
        if not isinstance(tenants, list) or not tenants or not all(
            isinstance(item, str) and IDENTIFIER.fullmatch(item)
            for item in tenants
        ):
            errors.append(
                f"line {line}: tenant_ids must be a non-empty identifier list"
            )
        elif len(set(tenants)) != len(tenants):
            errors.append(f"line {line}: tenant_ids must be unique")
        if not isinstance(document["published_at"], str):
            errors.append(f"line {line}: published_at must be an ISO date string")
        else:
            try:
                parsed_date = datetime.date.fromisoformat(
                    document["published_at"]
                )
                if parsed_date.isoformat() != document["published_at"]:
                    raise ValueError("date is not canonical")
            except ValueError:
                errors.append(
                    f"line {line}: published_at must be a canonical ISO date"
                )
        sections = document["sections"]
        if not isinstance(sections, list) or not sections:
            errors.append(f"line {line}: sections must be a non-empty list")
            continue
        section_ids: set[str] = set()
        for section in sections:
            if not isinstance(section, dict):
                errors.append(f"line {line}: section must be an object")
                continue
            if set(section) != {"section_id", "heading", "text"}:
                errors.append(f"line {line}: section has missing or unknown fields")
                continue
            section_id = section["section_id"]
            if not isinstance(section_id, str) or not IDENTIFIER.fullmatch(
                section_id
            ):
                errors.append(
                    f"line {line}: section_id must be a lowercase DNS-like identifier"
                )
                continue
            if section_id in section_ids:
                errors.append(f"line {line}: duplicate section_id {section_id!r}")
            section_ids.add(section_id)
            if not isinstance(section["heading"], str) or not normalize_text(
                section["heading"]
            ):
                errors.append(
                    f"line {line}: section {section_id!r} has empty heading"
                )
            if not isinstance(section["text"], str) or not normalize_text(
                section["text"]
            ):
                errors.append(f"line {line}: section {section_id!r} has empty text")
    if errors:
        raise ValueError("corpus validation failed:\n- " + "\n- ".join(errors))


def sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in SENTENCE.finditer(text):
        start, end = match.span()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((start, end))
    return spans


def chunk_section(
    text: str, target_words: int, overlap_sentences: int
) -> list[tuple[int, int, str]]:
    spans = sentence_spans(text)
    if not spans:
        return []
    chunks: list[tuple[int, int, str]] = []
    cursor = 0
    while cursor < len(spans):
        end_cursor = cursor
        words = 0
        while end_cursor < len(spans):
            candidate = text[spans[end_cursor][0] : spans[end_cursor][1]]
            candidate_words = len(TOKEN.findall(candidate.lower()))
            if end_cursor > cursor and words + candidate_words > target_words:
                break
            words += candidate_words
            end_cursor += 1
            if words >= target_words:
                break
        start = spans[cursor][0]
        end = spans[end_cursor - 1][1]
        chunks.append((start, end, text[start:end]))
        if end_cursor >= len(spans):
            break
        next_cursor = max(cursor + 1, end_cursor - overlap_sentences)
        cursor = next_cursor
    return chunks


def feature_stream(text: str) -> Iterable[str]:
    lowered = normalize_text(text).lower()
    words = TOKEN.findall(lowered)
    for word in words:
        yield f"w:{word}"
    collapsed = f"  {' '.join(words)}  "
    for index in range(max(0, len(collapsed) - 2)):
        yield f"c3:{collapsed[index:index + 3]}"


def hashing_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for feature in feature_stream(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [round(value / norm, 10) for value in vector]
    return vector


def build_records(
    documents: list[dict[str, Any]], config: dict[str, Any], source_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_documents: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    vectors: list[dict[str, Any]] = []
    target_words = int(config["chunking"]["target_words"])
    overlap_sentences = int(config["chunking"]["overlap_sentences"])
    dimensions = int(config["embedding"]["dimensions"])

    for source_document in documents:
        source_line = int(source_document["_source_line"])
        document = {
            key: value
            for key, value in source_document.items()
            if key != "_source_line"
        }
        source_hash = sha256_text(canonical_json(document))
        document["title"] = normalize_text(str(document["title"]))
        normalized_sections = []
        for section in document["sections"]:
            normalized_section = {
                "section_id": section["section_id"],
                "heading": normalize_text(section["heading"]),
                "text": normalize_text(section["text"]),
            }
            normalized_sections.append(normalized_section)
            for ordinal, (start, end, chunk_text) in enumerate(
                chunk_section(
                    normalized_section["text"], target_words, overlap_sentences
                )
            ):
                identity_material = "\0".join(
                    [
                        document["document_id"],
                        document["version"],
                        normalized_section["section_id"],
                        str(start),
                        str(end),
                        chunk_text,
                    ]
                )
                chunk_id = "chk_" + sha256_text(identity_material)[:24]
                chunk = {
                    "chunk_id": chunk_id,
                    "document_id": document["document_id"],
                    "document_version": document["version"],
                    "title": document["title"],
                    "source_uri": document["source_uri"],
                    "source_file": source_path.name,
                    "source_line": source_line,
                    "source_record_sha256": source_hash,
                    "license": document["license"],
                    "tenant_ids": sorted(document["tenant_ids"]),
                    "published_at": document["published_at"],
                    "section_id": normalized_section["section_id"],
                    "section_heading": normalized_section["heading"],
                    "chunk_ordinal": ordinal,
                    "offset_space": "normalized_section_text",
                    "start_char": start,
                    "end_char": end,
                    "text": chunk_text,
                    "text_sha256": sha256_text(chunk_text),
                }
                chunks.append(chunk)
                vectors.append(
                    {
                        "chunk_id": chunk_id,
                        "algorithm": config["embedding"]["algorithm"],
                        "dimensions": dimensions,
                        "normalized": True,
                        "vector": hashing_embedding(
                            f"{document['title']} {normalized_section['heading']} {chunk_text}",
                            dimensions,
                        ),
                    }
                )
        document["sections"] = normalized_sections
        document["source_file"] = source_path.name
        document["source_line"] = source_line
        document["source_record_sha256"] = source_hash
        normalized_documents.append(document)
    return normalized_documents, chunks, vectors


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(canonical_json(record) + "\n" for record in records),
        encoding="utf-8",
    )


def file_digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build(corpus: Path, config_path: Path, output: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    documents = read_jsonl(corpus)
    validate_documents(documents, set(config["allowed_licenses"]))
    normalized, chunks, vectors = build_records(documents, config, corpus)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "documents.jsonl", normalized)
    write_jsonl(output / "chunks.jsonl", chunks)
    write_jsonl(output / "vectors.jsonl", vectors)
    manifest = {
        "schema_version": 1,
        "source": {
            "path": corpus.name,
            "sha256": file_digest(corpus),
            "records": len(normalized),
        },
        "configuration": {
            "path": config_path.name,
            "sha256": file_digest(config_path),
            "value": config,
        },
        "outputs": {
            name: {
                "sha256": file_digest(output / name),
                "records": len(normalized if name == "documents.jsonl" else chunks),
            }
            for name in ("documents.jsonl", "chunks.jsonl")
        }
        | {
            "vectors.jsonl": {
                "sha256": file_digest(output / "vectors.jsonl"),
                "records": len(vectors),
            }
        },
        "lineage": {
            "offset_space": "normalized_section_text",
            "chunk_id_algorithm": "sha256(document_id, version, section_id, offsets, text)",
            "embedding_algorithm": config["embedding"]["algorithm"],
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build(args.corpus, args.config, args.output)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2
    print(
        f"built {manifest['source']['records']} documents and "
        f"{manifest['outputs']['chunks.jsonl']['records']} chunks in {args.output}"
    )
    print(f"source sha256={manifest['source']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
