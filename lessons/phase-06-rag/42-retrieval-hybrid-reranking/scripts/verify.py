#!/usr/bin/env python3
"""Verify component metrics and tenant isolation."""

from __future__ import annotations

import json
from pathlib import Path

LESSON = Path(__file__).resolve().parents[1]


def main() -> int:
    report = json.loads((LESSON / "artifacts/retrieval-results.json").read_text())
    assert report["schema_version"] == 1
    assert set(report["methods"]) == {"sparse", "dense", "hybrid", "reranked"}
    for method, values in report["methods"].items():
        assert 0 <= values["mean_recall_at_k"] <= 1, method
        assert 0 <= values["mean_mrr"] <= 1, method
        assert 0 <= values["mean_ndcg_at_k"] <= 1, method
        assert len(values["queries"]) == 8, method
    assert all(item["passed"] for item in report["security_cases"])
    assert all(not item["leaked_document_ids"] for item in report["security_cases"])
    candidates = json.loads((LESSON / "artifacts/example-candidates.json").read_text())
    assert candidates["filter_stage"] == "before_ranking"
    assert candidates["scored_chunk_count"] < candidates["corpus_chunk_count"]
    assert candidates["results"][0]["document_id"] == "alpha-access-policy"
    failures = json.loads((LESSON / "artifacts/failure-analysis.json").read_text())
    assert failures["failure_count"] == len(failures["failures"])
    assert failures["failure_count"] > 0
    print(
        "PASS: four retrieval paths produced bounded metrics; "
        "pre-ranking tenant filters blocked every forbidden document"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
