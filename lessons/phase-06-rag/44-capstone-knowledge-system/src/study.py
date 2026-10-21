#!/usr/bin/env python3
"""Record the four-variant contract study and corpus update/rollback proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

LESSON = Path(__file__).resolve().parents[1]
PHASE = LESSON.parent
L41 = PHASE / "41-ingestion-chunks-embeddings-indexes"
L42 = PHASE / "42-retrieval-hybrid-reranking"
L43 = PHASE / "43-grounded-generation-rag-evaluation-security"
sys.path.insert(0, str(L41 / "src"))
sys.path.insert(0, str(L42 / "src"))
sys.path.insert(0, str(L43 / "src"))

from grounding import GroundedSystem  # noqa: E402
from rag_ingest import build  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_system(corpus: Path, index_dir: Path) -> tuple[GroundedSystem, dict[str, Any]]:
    manifest = build(corpus, L41 / "configs/pipeline.json", index_dir)
    system = GroundedSystem(
        index_dir,
        json.loads((L42 / "configs/retrieval.json").read_text()),
        json.loads((L43 / "configs/grounding.json").read_text()),
    )
    return system, manifest


def variant_output(
    variant: str,
    question: dict[str, Any],
    grounded: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    configuration = contract["variants"][variant]
    has_retrieval = configuration["knowledge_mode"] == "retrieval"
    strict_json = configuration["behavior_mode"] == "strict_json"
    if has_retrieval:
        answer = grounded["answer"]
        citations = [
            span["citation_id"]
            for claim in grounded["claims"]
            for span in claim["source_spans"]
        ]
        abstained = grounded["abstained"]
    else:
        answer = "I do not have supplied evidence for this question."
        citations = []
        abstained = True
    if strict_json:
        structured = {
            "status": "insufficient_evidence" if abstained else "supported",
            "answer": answer,
            "citations": citations,
        }
        serialized = json.dumps(structured, sort_keys=True)
        format_valid = set(structured) == set(
            contract["acceptance"]["required_json_fields"]
        )
    else:
        structured = None
        serialized = answer
        format_valid = True
    phrase_passed = all(
        phrase.lower() in serialized.lower()
        for phrase in question["expected_phrases"]
    )
    citation_passed = bool(citations) if question["requires_citation"] else True
    abstention_contract = (not abstained) if has_retrieval else abstained
    return {
        "variant": variant,
        "implementation_class": configuration["implementation_class"],
        "input": {
            "question_id": question["id"],
            "tenant_id": question["tenant_id"],
            "question": question["question"],
        },
        "output": {
            "serialized": serialized,
            "structured": structured,
            "abstained": abstained,
            "citations": citations,
        },
        "checks": {
            "expected_phrases": phrase_passed,
            "format_valid": format_valid,
            "citation_present": citation_passed,
            "abstention_contract": abstention_contract,
        },
    }


def update_probe(
    fixture: dict[str, Any],
    v1_system: GroundedSystem,
    v2_system: GroundedSystem,
    rollback_system: GroundedSystem,
    manifests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    probe = fixture["update_probe"]
    records = []
    for name, system, expected in (
        ("v1", v1_system, probe["v1_expected_phrases"]),
        ("v2", v2_system, probe["v2_expected_phrases"]),
        ("rollback", rollback_system, probe["v1_expected_phrases"]),
    ):
        result = system.answer(probe["question"], probe["tenant_id"])
        records.append(
            {
                "stage": name,
                "source_sha256": manifests[name]["source"]["sha256"],
                "answer": result["answer"],
                "citations": [
                    span
                    for claim in result["claims"]
                    for span in claim["source_spans"]
                ],
                "expected_phrases_passed": all(
                    phrase.lower() in result["answer"].lower() for phrase in expected
                ),
            }
        )
    return {
        "v1": records[0],
        "v2": records[1],
        "rollback": records[2],
        "changed_on_update": records[0]["answer"] != records[1]["answer"],
        "rollback_exact": records[0]["answer"] == records[2]["answer"],
        "rollback_citations_exact": (
            records[0]["citations"] == records[2]["citations"]
        ),
        "v1_manifest_matches_rollback": manifests["v1"] == manifests["rollback"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    fixture = json.loads(args.questions.read_text())
    args.work_dir.mkdir(parents=True, exist_ok=True)
    v1_system, v1_manifest = make_system(
        L41 / "data/corpus-v1.jsonl", args.work_dir / "index-v1"
    )
    v2_system, v2_manifest = make_system(
        L41 / "data/corpus-v2.jsonl", args.work_dir / "index-v2"
    )
    rollback_system, rollback_manifest = make_system(
        L41 / "data/corpus-v1.jsonl", args.work_dir / "index-rollback"
    )
    records = []
    for question in fixture["questions"]:
        grounded = v1_system.answer(question["question"], question["tenant_id"])
        for variant in contract["variants"]:
            records.append(
                variant_output(variant, question, grounded, contract)
            )
    summaries = {}
    for variant in contract["variants"]:
        relevant = [item for item in records if item["variant"] == variant]
        summaries[variant] = {
            "implementation_class": contract["variants"][variant][
                "implementation_class"
            ],
            "questions": len(relevant),
            "expected_phrase_rate": sum(
                item["checks"]["expected_phrases"] for item in relevant
            )
            / len(relevant),
            "format_rate": sum(item["checks"]["format_valid"] for item in relevant)
            / len(relevant),
            "citation_rate": sum(
                item["checks"]["citation_present"] for item in relevant
            )
            / len(relevant),
            "abstention_contract_rate": sum(
                item["checks"]["abstention_contract"] for item in relevant
            )
            / len(relevant),
        }
    update = update_probe(
        fixture,
        v1_system,
        v2_system,
        rollback_system,
        {"v1": v1_manifest, "v2": v2_manifest, "rollback": rollback_manifest},
    )
    report = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(args.contract),
        "question_fixture_sha256": sha256(args.questions),
        "interpretation": contract["interpretation"],
        "variants": summaries,
        "records": records,
        "update_rollback": update,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("recorded four variants across", len(fixture["questions"]), "questions")
    print(
        "update changed answer=",
        update["changed_on_update"],
        "rollback exact=",
        update["rollback_exact"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
