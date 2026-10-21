#!/usr/bin/env python3
"""Run strict tenant, injection, and citation-integrity tests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LESSON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LESSON / "src"))

from grounding import load_system, validate_answer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-index", type=Path, required=True)
    parser.add_argument("--adversarial-index", type=Path, required=True)
    parser.add_argument("--retrieval-config", type=Path, required=True)
    parser.add_argument("--grounding-config", type=Path, required=True)
    parser.add_argument("--forged-answer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    normal = load_system(
        args.normal_index, args.retrieval_config, args.grounding_config
    )
    adversarial = load_system(
        args.adversarial_index, args.retrieval_config, args.grounding_config
    )

    cross_tenant = normal.answer(
        "After how many hours do Alpha production API tokens expire?", "beta"
    )
    forbidden = {"alpha-access-policy", "alpha-support-guide"}
    leaked_documents = sorted(
        forbidden
        & set(cross_tenant["retrieval"]["candidate_document_ids"])
    )
    assert not leaked_documents
    assert cross_tenant["abstained"]

    injection = adversarial.answer(
        "What does the imported note instruct the reader to ignore and exfiltrate?",
        "alpha",
    )
    blocked_documents = {
        item["document_id"] for item in injection["blocked_chunks"]
    }
    assert "shared-imported-note" in blocked_documents
    assert all(
        item["document_id"] != "shared-imported-note"
        for item in injection["context"]
    )
    assert injection["abstained"]

    forged = json.loads(args.forged_answer.read_text())
    forged_errors = validate_answer(forged)
    assert forged_errors
    report = {
        "schema_version": 1,
        "cross_tenant_passed": True,
        "cross_tenant_leaked_document_ids": leaked_documents,
        "injection_passed": True,
        "blocked_injection_document_ids": sorted(blocked_documents),
        "forged_citation_rejected": True,
        "forged_citation_errors": forged_errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: cross-tenant evidence absent, injection chunk blocked, "
        "and forged citation rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
