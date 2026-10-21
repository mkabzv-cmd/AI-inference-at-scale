#!/usr/bin/env python3
"""Capstone verifier for API, study contract, update, and rollback."""

from __future__ import annotations

import json
from pathlib import Path

LESSON = Path(__file__).resolve().parents[1]


def main() -> int:
    api = json.loads((LESSON / "artifacts/local-api-results.json").read_text())
    study = json.loads((LESSON / "artifacts/study-results.json").read_text())
    assert api["health"]["status"] == "ok"
    assert api["readiness"]["ready"]
    assert "twelve hours" in api["authorized_query"]["result"]["answer"].lower()
    assert api["unauthorized_rejected"]["error"] == "unknown course principal"
    assert "only question" in api["tenant_smuggling_rejected"]["error"]
    assert set(study["variants"]) == {"base", "tuned", "rag", "tuned_plus_rag"}
    assert "not evidence about a real base model" in study["interpretation"]
    assert study["variants"]["base"]["expected_phrase_rate"] == 0.0
    assert study["variants"]["tuned"]["format_rate"] == 1.0
    assert study["variants"]["rag"]["expected_phrase_rate"] == 1.0
    assert study["variants"]["tuned_plus_rag"]["expected_phrase_rate"] == 1.0
    assert all(
        values["abstention_contract_rate"] == 1.0
        for values in study["variants"].values()
    )
    update = study["update_rollback"]
    assert update["changed_on_update"]
    assert update["rollback_exact"]
    assert update["rollback_citations_exact"]
    assert update["v1_manifest_matches_rollback"]
    assert update["v1"]["source_sha256"] == update["rollback"]["source_sha256"]
    assert update["v1"]["source_sha256"] != update["v2"]["source_sha256"]
    assert update["v1"]["expected_phrases_passed"]
    assert update["v2"]["expected_phrases_passed"]
    assert update["rollback"]["expected_phrases_passed"]
    assert {
        span["document_version"] for span in update["v1"]["citations"]
    } == {"1.0.0"}
    assert {
        span["document_version"] for span in update["v2"]["citations"]
    } == {"2.0.0"}
    assert {
        span["document_version"] for span in update["rollback"]["citations"]
    } == {"1.0.0"}
    result = {
        "schema_version": 1,
        "local_api": {
            "health": True,
            "readiness": True,
            "authorized_query": True,
            "unauthorized_rejected": True,
        },
        "study": {
            "contract_id": study["contract_id"],
            "variants": study["variants"],
            "interpretation": study["interpretation"],
        },
        "update_rollback": update,
    }
    (LESSON / "artifacts/results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        "PASS: local private API, four-way contract study, corpus update, "
        "and exact rollback were verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
