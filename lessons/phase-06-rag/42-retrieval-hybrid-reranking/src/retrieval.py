#!/usr/bin/env python3
"""BM25, dense, RRF, transparent reranking, and component evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

LESSON = Path(__file__).resolve().parents[1]
PHASE = LESSON.parent
L41_SRC = PHASE / "41-ingestion-chunks-embeddings-indexes/src"
sys.path.insert(0, str(L41_SRC))

from rag_ingest import hashing_embedding  # noqa: E402
from vector_search import dot  # noqa: E402

TOKEN = re.compile(r"[a-z0-9]+")
METHODS = ("sparse", "dense", "hybrid", "reranked")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def validate_config(config: dict[str, Any]) -> None:
    errors = []
    if config.get("filter_stage") != "before_ranking":
        errors.append("filter_stage must be before_ranking")
    top_k = config.get("top_k")
    candidate_k = config.get("candidate_k")
    if not isinstance(top_k, int) or top_k < 1:
        errors.append("top_k must be a positive integer")
    if not isinstance(candidate_k, int) or candidate_k < max(1, top_k or 1):
        errors.append("candidate_k must be at least top_k")
    bm25 = config.get("bm25", {})
    if not isinstance(bm25.get("k1"), (int, float)) or bm25.get("k1", 0) <= 0:
        errors.append("bm25.k1 must be positive")
    if not isinstance(bm25.get("b"), (int, float)) or not 0 <= bm25.get("b", -1) <= 1:
        errors.append("bm25.b must be between zero and one")
    rrf = config.get("rrf", {})
    if not isinstance(rrf.get("rank_constant"), int) or rrf.get("rank_constant", 0) <= 0:
        errors.append("rrf.rank_constant must be a positive integer")
    weights = [rrf.get("sparse_weight"), rrf.get("dense_weight")]
    if not all(isinstance(value, (int, float)) and value >= 0 for value in weights):
        errors.append("RRF weights must be non-negative")
    if not any(isinstance(value, (int, float)) and value > 0 for value in weights):
        errors.append("at least one RRF weight must be positive")
    reranker = config.get("reranker", {})
    rerank_weights = [
        reranker.get("base_weight"),
        reranker.get("token_overlap_weight"),
        reranker.get("heading_overlap_weight"),
    ]
    if not all(
        isinstance(value, (int, float)) and value >= 0 for value in rerank_weights
    ):
        errors.append("reranker weights must be non-negative")
    if not math.isclose(sum(rerank_weights), 1.0, abs_tol=1e-9):
        errors.append("reranker weights must sum to one")
    if errors:
        raise ValueError("invalid retrieval configuration:\n- " + "\n- ".join(errors))


class Retriever:
    def __init__(self, index_dir: Path, config: dict[str, Any]) -> None:
        validate_config(config)
        self.config = config
        self.index_dir = index_dir
        self.chunks = read_jsonl(index_dir / "chunks.jsonl")
        vector_records = read_jsonl(index_dir / "vectors.jsonl")
        if not self.chunks or not vector_records:
            raise ValueError("index must contain chunks and vectors")
        chunk_ids = [item["chunk_id"] for item in self.chunks]
        vector_ids = [item["chunk_id"] for item in vector_records]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("index contains duplicate chunk IDs")
        if len(set(vector_ids)) != len(vector_ids):
            raise ValueError("index contains duplicate vector IDs")
        if set(chunk_ids) != set(vector_ids):
            raise ValueError("chunk and vector ID sets differ")
        self.vectors = {item["chunk_id"]: item["vector"] for item in vector_records}
        self.dimensions = int(vector_records[0]["dimensions"])
        if self.dimensions < 1 or any(
            int(item["dimensions"]) != self.dimensions
            or len(item["vector"]) != self.dimensions
            for item in vector_records
        ):
            raise ValueError("vector dimensions are inconsistent")
        self.chunk_by_id = {item["chunk_id"]: item for item in self.chunks}

    def authorized(self, tenant_id: str) -> list[dict[str, Any]]:
        return [item for item in self.chunks if tenant_id in item["tenant_ids"]]

    def _bm25(
        self, query: str, corpus: list[dict[str, Any]]
    ) -> list[tuple[str, float]]:
        query_terms = tokenize(query)
        tokenized = [
            tokenize(f"{chunk['title']} {chunk['section_heading']} {chunk['text']}")
            for chunk in corpus
        ]
        average_length = statistics.fmean(len(tokens) for tokens in tokenized) if tokenized else 0
        document_frequency = Counter(
            term for term in set(query_terms) for tokens in tokenized if term in set(tokens)
        )
        k1 = float(self.config["bm25"]["k1"])
        b = float(self.config["bm25"]["b"])
        scores = []
        total = len(corpus)
        for chunk, tokens in zip(corpus, tokenized):
            counts = Counter(tokens)
            score = 0.0
            for term in query_terms:
                frequency = counts[term]
                if frequency == 0:
                    continue
                df = document_frequency[term]
                inverse_frequency = math.log(1 + (total - df + 0.5) / (df + 0.5))
                length_normalizer = 1 - b + b * len(tokens) / max(1.0, average_length)
                score += inverse_frequency * (
                    frequency * (k1 + 1)
                    / (frequency + k1 * length_normalizer)
                )
            scores.append((chunk["chunk_id"], score))
        return sorted(scores, key=lambda item: (-item[1], item[0]))

    def _dense(
        self, query: str, corpus: list[dict[str, Any]]
    ) -> list[tuple[str, float]]:
        query_vector = hashing_embedding(query, self.dimensions)
        scores = [
            (chunk["chunk_id"], dot(query_vector, self.vectors[chunk["chunk_id"]]))
            for chunk in corpus
        ]
        return sorted(scores, key=lambda item: (-item[1], item[0]))

    def _rrf(
        self,
        sparse: list[tuple[str, float]],
        dense: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        constant = self.config["rrf"]["rank_constant"]
        weights = {
            "sparse": self.config["rrf"]["sparse_weight"],
            "dense": self.config["rrf"]["dense_weight"],
        }
        scores: defaultdict[str, float] = defaultdict(float)
        for method, ranking in (("sparse", sparse), ("dense", dense)):
            for rank_index, (chunk_id, _score) in enumerate(ranking, 1):
                scores[chunk_id] += weights[method] / (constant + rank_index)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))

    def _rerank(
        self, query: str, hybrid: list[tuple[str, float]]
    ) -> list[tuple[str, float]]:
        query_tokens = set(tokenize(query))
        maximum_base = max((score for _chunk_id, score in hybrid), default=1.0)
        weights = self.config["reranker"]
        scored = []
        for chunk_id, base_score in hybrid[: self.config["candidate_k"]]:
            chunk = self.chunk_by_id[chunk_id]
            text_tokens = set(tokenize(chunk["text"]))
            heading_tokens = set(tokenize(chunk["section_heading"]))
            token_overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))
            heading_overlap = len(query_tokens & heading_tokens) / max(1, len(query_tokens))
            normalized_base = base_score / maximum_base if maximum_base else 0.0
            score = (
                weights["base_weight"] * normalized_base
                + weights["token_overlap_weight"] * token_overlap
                + weights["heading_overlap_weight"] * heading_overlap
            )
            scored.append((chunk_id, score))
        return sorted(scored, key=lambda item: (-item[1], item[0]))

    def retrieve(
        self, query: str, tenant_id: str, method: str, top_k: Optional[int] = None
    ) -> dict[str, Any]:
        if method not in METHODS:
            raise ValueError(f"unknown method {method!r}")
        if top_k is None:
            top_k = int(self.config["top_k"])
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        started = time.perf_counter_ns()
        authorized = self.authorized(tenant_id)
        if method == "sparse":
            selected_ranking = self._bm25(query, authorized)
        elif method == "dense":
            selected_ranking = self._dense(query, authorized)
        else:
            sparse = self._bm25(query, authorized)
            dense = self._dense(query, authorized)
            hybrid = self._rrf(
                sparse[: self.config["candidate_k"]],
                dense[: self.config["candidate_k"]],
            )
            selected_ranking = (
                hybrid if method == "hybrid" else self._rerank(query, hybrid)
            )
        elapsed = time.perf_counter_ns() - started
        selected = selected_ranking[:top_k]
        return {
            "query": query,
            "tenant_id": tenant_id,
            "method": method,
            "filter_stage": "before_ranking",
            "corpus_chunk_count": len(self.chunks),
            "scored_chunk_count": len(authorized),
            "elapsed_ns": elapsed,
            "results": [
                {
                    "rank": rank,
                    "score": round(score, 10),
                    **self.chunk_by_id[chunk_id],
                }
                for rank, (chunk_id, score) in enumerate(selected, 1)
            ],
        }


def dcg(grades: list[int]) -> float:
    return sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(grades, 1)
    )


def metrics_for(ranked_ids: list[str], relevance: dict[str, int]) -> dict[str, float]:
    relevant = set(relevance)
    hits = [chunk_id for chunk_id in ranked_ids if chunk_id in relevant]
    recall = len(hits) / len(relevant) if relevant else 1.0
    reciprocal_rank = next(
        (1.0 / rank for rank, chunk_id in enumerate(ranked_ids, 1) if chunk_id in relevant),
        0.0,
    )
    grades = [int(relevance.get(chunk_id, 0)) for chunk_id in ranked_ids]
    ideal = sorted((int(value) for value in relevance.values()), reverse=True)[: len(ranked_ids)]
    ideal_dcg = dcg(ideal)
    return {
        "recall_at_k": recall,
        "mrr": reciprocal_rank,
        "ndcg_at_k": dcg(grades) / ideal_dcg if ideal_dcg else 1.0,
    }


def validate_qrels(
    fixture: dict[str, Any],
    retriever: Retriever,
    manifest: dict[str, Any],
) -> None:
    errors = []
    if fixture.get("index_source_sha256") != manifest["source"]["sha256"]:
        errors.append("qrels index_source_sha256 does not match the active corpus")
    seen = set()
    for query in fixture.get("queries", []):
        query_id = query.get("id")
        if query_id in seen:
            errors.append(f"duplicate query id {query_id!r}")
        seen.add(query_id)
        tenant_id = query.get("tenant_id")
        relevance = query.get("relevance")
        if not isinstance(relevance, dict) or not relevance:
            errors.append(f"query {query_id}: relevance must be a non-empty object")
            continue
        for chunk_id, grade in relevance.items():
            if (
                not isinstance(grade, int)
                or isinstance(grade, bool)
                or not 1 <= grade <= 3
            ):
                errors.append(
                    f"query {query_id}: grade for {chunk_id} must be 1, 2, or 3"
                )
            chunk = retriever.chunk_by_id.get(chunk_id)
            if chunk is None:
                errors.append(f"query {query_id}: unknown relevant chunk {chunk_id}")
            elif tenant_id not in chunk["tenant_ids"]:
                errors.append(
                    f"query {query_id}: relevant chunk {chunk_id} is unauthorized for {tenant_id}"
                )
    if errors:
        raise ValueError("invalid qrels:\n- " + "\n- ".join(errors))


def validate_security_cases(
    fixture: dict[str, Any], retriever: Retriever
) -> None:
    errors = []
    seen = set()
    chunks_by_document: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in retriever.chunks:
        chunks_by_document[chunk["document_id"]].append(chunk)
    for case in fixture.get("cases", []):
        case_id = case.get("id")
        if case_id in seen:
            errors.append(f"duplicate security case id {case_id!r}")
        seen.add(case_id)
        tenant_id = case.get("tenant_id")
        forbidden = case.get("forbidden_document_ids")
        if not isinstance(forbidden, list) or not forbidden:
            errors.append(
                f"security case {case_id}: forbidden_document_ids must be non-empty"
            )
            continue
        for document_id in forbidden:
            chunks = chunks_by_document.get(document_id, [])
            if not chunks:
                errors.append(
                    f"security case {case_id}: unknown forbidden document {document_id}"
                )
            elif any(tenant_id in chunk["tenant_ids"] for chunk in chunks):
                errors.append(
                    f"security case {case_id}: forbidden document {document_id} "
                    f"is authorized for {tenant_id}"
                )
    if errors:
        raise ValueError(
            "invalid security cases:\n- " + "\n- ".join(errors)
        )


def evaluate(
    retriever: Retriever,
    qrels_path: Path,
    security_path: Path,
    output: Path,
) -> dict[str, Any]:
    fixture = json.loads(qrels_path.read_text())
    manifest = json.loads((retriever.index_dir / "manifest.json").read_text())
    validate_qrels(fixture, retriever, manifest)
    by_method: dict[str, list[dict[str, Any]]] = {method: [] for method in METHODS}
    for query in fixture["queries"]:
        for method in METHODS:
            result = retriever.retrieve(
                query["text"], query["tenant_id"], method, retriever.config["top_k"]
            )
            ranked_ids = [item["chunk_id"] for item in result["results"]]
            by_method[method].append(
                {
                    "query_id": query["id"],
                    **metrics_for(ranked_ids, query["relevance"]),
                    "elapsed_ns": result["elapsed_ns"],
                    "ranked_chunk_ids": ranked_ids,
                }
            )
    method_reports = {}
    for method, cases in by_method.items():
        method_reports[method] = {
            "mean_recall_at_k": statistics.fmean(item["recall_at_k"] for item in cases),
            "mean_mrr": statistics.fmean(item["mrr"] for item in cases),
            "mean_ndcg_at_k": statistics.fmean(item["ndcg_at_k"] for item in cases),
            "median_elapsed_ns": int(statistics.median(item["elapsed_ns"] for item in cases)),
            "queries": cases,
            "latency_note": "Tiny local component timing; not a production capacity result.",
        }

    security_fixture = json.loads(security_path.read_text())
    validate_security_cases(security_fixture, retriever)
    security_reports = []
    for case in security_fixture["cases"]:
        for method in METHODS:
            result = retriever.retrieve(case["text"], case["tenant_id"], method, 20)
            returned_documents = {item["document_id"] for item in result["results"]}
            leaked = sorted(returned_documents & set(case["forbidden_document_ids"]))
            security_reports.append(
                {
                    "case_id": case["id"],
                    "method": method,
                    "passed": not leaked,
                    "leaked_document_ids": leaked,
                    "scored_chunk_count": result["scored_chunk_count"],
                }
            )

    report = {
        "schema_version": 1,
        "index_manifest_sha256": hashlib.sha256(
            (retriever.index_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "top_k": retriever.config["top_k"],
        "methods": method_reports,
        "security_cases": security_reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def load(config_path: Path, index_path: Path) -> Retriever:
    return Retriever(index_path, json.loads(config_path.read_text()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--text", required=True)
    query_parser.add_argument("--tenant", required=True)
    query_parser.add_argument("--method", choices=METHODS, required=True)
    query_parser.add_argument("--top-k", type=int, default=3)
    evaluation_parser = subparsers.add_parser("evaluate")
    evaluation_parser.add_argument("--qrels", type=Path, required=True)
    evaluation_parser.add_argument("--security-cases", type=Path, required=True)
    evaluation_parser.add_argument("--output", type=Path, required=True)
    validation_parser = subparsers.add_parser("validate-qrels")
    validation_parser.add_argument("--qrels", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        retriever = load(args.config, args.index)
        if args.command == "query":
            report = retriever.retrieve(
                args.text, args.tenant, args.method, args.top_k
            )
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "evaluate":
            report = evaluate(
                retriever, args.qrels, args.security_cases, args.output
            )
            for method in METHODS:
                values = report["methods"][method]
                print(
                    f"{method}: recall@{report['top_k']}="
                    f"{values['mean_recall_at_k']:.3f} "
                    f"MRR={values['mean_mrr']:.3f} "
                    f"nDCG@{report['top_k']}={values['mean_ndcg_at_k']:.3f}"
                )
        else:
            fixture = json.loads(args.qrels.read_text())
            manifest = json.loads((args.index / "manifest.json").read_text())
            validate_qrels(fixture, retriever, manifest)
            print("PASS: qrels match active index and tenant entitlements")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
