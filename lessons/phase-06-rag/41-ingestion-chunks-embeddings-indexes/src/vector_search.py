#!/usr/bin/env python3
"""Search exact vectors and a deliberately small LSH candidate index."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from rag_ingest import hashing_embedding


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def dot(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return sum(a * b for a, b in zip(left, right))


def norm(vector: list[float]) -> float:
    return math.sqrt(dot(vector, vector))


def cosine(left: list[float], right: list[float]) -> float:
    denominator = norm(left) * norm(right)
    return dot(left, right) / denominator if denominator else 0.0


def l2(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def hyperplane(plane_id: int, dimensions: int) -> list[float]:
    values = []
    for dimension in range(dimensions):
        digest = hashlib.sha256(f"plane:{plane_id}:{dimension}".encode()).digest()
        values.append(1.0 if digest[0] & 1 else -1.0)
    return values


def signature(vector: list[float], planes: int) -> str:
    return "".join(
        "1" if dot(vector, hyperplane(index, len(vector))) >= 0 else "0"
        for index in range(planes)
    )


def hamming(left: str, right: str) -> int:
    if len(left) != len(right):
        raise ValueError("signatures differ in width")
    return sum(a != b for a, b in zip(left, right))


def eligible_chunks(
    chunks: list[dict[str, Any]], tenant_id: str
) -> list[dict[str, Any]]:
    return [chunk for chunk in chunks if tenant_id in chunk["tenant_ids"]]


def rank(
    chunks: list[dict[str, Any]],
    vectors: dict[str, list[float]],
    query_vector: list[float],
    metric: str,
    top_k: int,
) -> list[dict[str, Any]]:
    results = []
    for chunk in chunks:
        vector = vectors[chunk["chunk_id"]]
        if metric == "cosine":
            raw_score = cosine(query_vector, vector)
            sort_score = raw_score
        elif metric == "dot":
            raw_score = dot(query_vector, vector)
            sort_score = raw_score
        elif metric == "l2":
            raw_score = l2(query_vector, vector)
            sort_score = -raw_score
        else:
            raise ValueError(f"unknown metric {metric!r}")
        results.append(
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "section_id": chunk["section_id"],
                "score": round(raw_score, 8),
                "_sort_score": sort_score,
            }
        )
    results.sort(key=lambda item: (-item["_sort_score"], item["chunk_id"]))
    for item in results:
        item.pop("_sort_score")
    return results[:top_k]


def search(
    index_dir: Path,
    query: str,
    tenant_id: str,
    top_k: int,
    metric: str = "cosine",
    approximate: bool = False,
) -> dict[str, Any]:
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    chunks = read_jsonl(index_dir / "chunks.jsonl")
    vector_records = read_jsonl(index_dir / "vectors.jsonl")
    if not chunks or not vector_records:
        raise ValueError("index must contain chunks and vectors")
    chunk_ids = [record["chunk_id"] for record in chunks]
    vector_ids = [record["chunk_id"] for record in vector_records]
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("index contains duplicate chunk IDs")
    if len(set(vector_ids)) != len(vector_ids):
        raise ValueError("index contains duplicate vector IDs")
    if set(chunk_ids) != set(vector_ids):
        raise ValueError("chunk and vector ID sets differ")
    vectors = {record["chunk_id"]: record["vector"] for record in vector_records}
    dimensions = int(vector_records[0]["dimensions"])
    if dimensions < 1 or any(
        int(record["dimensions"]) != dimensions
        or len(record["vector"]) != dimensions
        for record in vector_records
    ):
        raise ValueError("vector dimensions are inconsistent")
    config = json.loads((index_dir / "manifest.json").read_text())["configuration"]["value"]
    started = time.perf_counter_ns()
    query_vector = hashing_embedding(query, dimensions)
    authorized = eligible_chunks(chunks, tenant_id)
    candidate_chunks = authorized
    query_signature = None
    if approximate:
        planes = int(config["approximate_index"]["hyperplanes"])
        max_distance = int(config["approximate_index"]["max_hamming_distance"])
        query_signature = signature(query_vector, planes)
        candidate_chunks = [
            chunk
            for chunk in authorized
            if hamming(signature(vectors[chunk["chunk_id"]], planes), query_signature)
            <= max_distance
        ]
    results = rank(candidate_chunks, vectors, query_vector, metric, top_k)
    elapsed = time.perf_counter_ns() - started
    return {
        "query": query,
        "tenant_id": tenant_id,
        "metric": metric,
        "approximate": approximate,
        "authorized_chunks": len(authorized),
        "candidate_chunks": len(candidate_chunks),
        "query_signature": query_signature,
        "elapsed_ns": elapsed,
        "results": results,
    }


def benchmark(index_dir: Path, queries_path: Path, output_path: Path) -> dict[str, Any]:
    query_fixture = json.loads(queries_path.read_text(encoding="utf-8"))
    cases = []
    exact_latencies = []
    approximate_latencies = []
    for query in query_fixture["queries"]:
        exact = search(index_dir, query["text"], query["tenant_id"], 3, "cosine", False)
        approximate = search(
            index_dir, query["text"], query["tenant_id"], 3, "cosine", True
        )
        exact_ids = [item["chunk_id"] for item in exact["results"]]
        approximate_ids = [item["chunk_id"] for item in approximate["results"]]
        overlap = len(set(exact_ids) & set(approximate_ids))
        relevant_pairs = {
            (item["document_id"], item["section_id"]) for item in query["relevant"]
        }
        relevant_hit = any(
            (item["document_id"], item["section_id"]) in relevant_pairs
            for item in exact["results"]
        )
        exact_latencies.append(exact["elapsed_ns"])
        approximate_latencies.append(approximate["elapsed_ns"])
        cases.append(
            {
                "query_id": query["id"],
                "relevant_hit_in_exact_top_3": relevant_hit,
                "exact_top_3": exact_ids,
                "approximate_top_3": approximate_ids,
                "approximate_recall_against_exact_top_3": overlap
                / max(1, len(exact_ids)),
                "approximate_candidates": approximate["candidate_chunks"],
            }
        )
    report = {
        "schema_version": 1,
        "queries": cases,
        "exact": {
            "median_query_path_ns": int(statistics.median(exact_latencies)),
            "note": "Measured on this tiny local fixture; not a production benchmark.",
        },
        "approximate": {
            "median_query_path_ns": int(statistics.median(approximate_latencies)),
            "mean_recall_against_exact_top_3": statistics.fmean(
                case["approximate_recall_against_exact_top_3"] for case in cases
            ),
            "note": "LSH limits candidates and may return fewer than k results.",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--index", type=Path, required=True)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--tenant", required=True)
    search_parser.add_argument("--top-k", type=int, default=3)
    search_parser.add_argument("--metric", choices=("cosine", "dot", "l2"), default="cosine")
    search_parser.add_argument("--approximate", action="store_true")
    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--index", type=Path, required=True)
    benchmark_parser.add_argument("--queries", type=Path, required=True)
    benchmark_parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "search":
        result = search(
            args.index,
            args.query,
            args.tenant,
            args.top_k,
            args.metric,
            args.approximate,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        result = benchmark(args.index, args.queries, args.output)
        print(
            "benchmark complete: "
            f"mean ANN recall@3 vs exact={result['approximate']['mean_recall_against_exact_top_3']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
