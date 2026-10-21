#!/usr/bin/env python3
"""Verify retrieval/answer separation and strict security evidence."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

LESSON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LESSON / "src"))

from grounding import validate_answer  # noqa: E402


def main() -> int:
    grounding = json.loads((LESSON / "artifacts/grounding-results.json").read_text())
    security = json.loads((LESSON / "artifacts/security-results.json").read_text())
    assert grounding["retrieval_metrics"]["answerable_hit_rate"] == 1.0
    assert 0.0 <= grounding["retrieval_metrics"]["mean_recall_at_k"] <= 1.0
    assert grounding["answer_metrics"]["expected_phrase_rate"] == 1.0
    assert grounding["answer_metrics"]["abstention_accuracy"] == 1.0
    assert grounding["answer_metrics"]["supported_claim_rate"] == 1.0
    assert all(
        not case["leaked_forbidden_document_ids"] for case in grounding["cases"]
    )
    assert security["cross_tenant_passed"]
    assert security["injection_passed"]
    assert security["forged_citation_rejected"]
    example = json.loads((LESSON / "artifacts/example-answer.json").read_text())
    assert "[S" in example["answer"] and example["claims"]
    assert all(item["trust"] == "untrusted_document_content" for item in example["context"])
    assert not validate_answer(example)
    tampered = copy.deepcopy(example)
    tampered_span = tampered["claims"][0]["source_spans"][0]
    tampered_span["source_start_char"] += 1
    tampered_span["source_end_char"] += 1
    assert any(
        "quote and offsets do not map to context" in error
        for error in validate_answer(tampered)
    )
    combined = {
        "schema_version": 1,
        "retrieval_metrics": grounding["retrieval_metrics"],
        "answer_metrics": grounding["answer_metrics"],
        "security": security,
    }
    (LESSON / "artifacts/results.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n"
    )
    print(
        "PASS: retrieval and answer metrics passed separately; citations, "
        "abstention, tenant isolation, and injection blocking verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
