#!/usr/bin/env python3
"""Verify lineage, metric identities, tenancy, and benchmark honesty."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

LESSON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LESSON / "src"))

from rag_ingest import canonical_json  # noqa: E402
from vector_search import search  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> int:
    index = LESSON / "artifacts/index-a"
    documents = read_jsonl(index / "documents.jsonl")
    chunks = read_jsonl(index / "chunks.jsonl")
    vectors = read_jsonl(index / "vectors.jsonl")
    documents_by_identity = {
        (item["document_id"], item["version"]): item for item in documents
    }
    source_documents = [
        json.loads(line)
        for line in (LESSON / "data/corpus-v1.jsonl").read_text().splitlines()
        if line
    ]
    source_hashes = {
        (item["document_id"], item["version"]): hashlib.sha256(
            canonical_json(item).encode()
        ).hexdigest()
        for item in source_documents
    }
    assert chunks and len(chunks) == len(vectors)
    assert len({item["chunk_id"] for item in chunks}) == len(chunks)
    assert set(documents_by_identity) == set(source_hashes)
    for identity, document in documents_by_identity.items():
        assert document["source_record_sha256"] == source_hashes[identity]
    for chunk in chunks:
        document = documents_by_identity[
            (chunk["document_id"], chunk["document_version"])
        ]
        assert chunk["source_record_sha256"] == source_hashes[
            (chunk["document_id"], chunk["document_version"])
        ]
        section = next(
            item for item in document["sections"] if item["section_id"] == chunk["section_id"]
        )
        recovered = section["text"][chunk["start_char"] : chunk["end_char"]]
        assert recovered == chunk["text"]
        assert hashlib.sha256(recovered.encode()).hexdigest() == chunk["text_sha256"]

    cosine = search(index, "API token expiry", "alpha", 5, "cosine")
    dot = search(index, "API token expiry", "alpha", 5, "dot")
    l2 = search(index, "API token expiry", "alpha", 5, "l2")
    cosine_ids = [item["chunk_id"] for item in cosine["results"]]
    assert cosine_ids == [item["chunk_id"] for item in dot["results"]]
    assert cosine_ids == [item["chunk_id"] for item in l2["results"]]
    assert len(cosine["results"]) == len(dot["results"]) == len(l2["results"])
    for cosine_item, dot_item, l2_item in zip(
        cosine["results"], dot["results"], l2["results"]
    ):
        assert math.isclose(cosine_item["score"], dot_item["score"], abs_tol=1e-7)
        expected_l2 = math.sqrt(max(0.0, 2.0 - 2.0 * dot_item["score"]))
        assert math.isclose(l2_item["score"], expected_l2, abs_tol=1e-6)

    beta = search(index, "production token", "beta", 20, "cosine")
    assert all(item["document_id"] != "alpha-access-policy" for item in beta["results"])
    benchmark = json.loads((LESSON / "artifacts/index-benchmark.json").read_text())
    assert all(case["relevant_hit_in_exact_top_3"] for case in benchmark["queries"])
    assert 0.0 <= benchmark["approximate"]["mean_recall_against_exact_top_3"] <= 1.0
    manifest = json.loads((index / "manifest.json").read_text())
    assert manifest["source"]["sha256"] == hashlib.sha256(
        (LESSON / "data/corpus-v1.jsonl").read_bytes()
    ).hexdigest()
    for name, metadata in manifest["outputs"].items():
        assert metadata["sha256"] == hashlib.sha256(
            (index / name).read_bytes()
        ).hexdigest()

    manifest_hash = hashlib.sha256((index / "manifest.json").read_bytes()).hexdigest()
    result = {
        "schema_version": 1,
        "corpus": {
            "documents": len(documents),
            "chunks": len(chunks),
            "manifest_sha256": manifest_hash,
        },
        "exact": {"metric_order_equivalent_for_normalized_vectors": True},
        "approximate": benchmark["approximate"],
        "lineage_verified": True,
    }
    (LESSON / "artifacts/results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"PASS: traced {len(chunks)} chunks to normalized source offsets; "
        "tenant filter and normalized-vector metric identities verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
