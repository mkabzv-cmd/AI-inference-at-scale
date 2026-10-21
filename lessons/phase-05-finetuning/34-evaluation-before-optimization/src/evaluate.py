#!/usr/bin/env python3
"""Evaluate frozen acceptance examples with inspectable deterministic metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def term_present(term: str, response: str) -> bool:
    normalized_term = normalize(term)
    normalized_response = normalize(response)
    if normalized_term == "endpoints":
        return "endpoint" in normalized_response
    return normalized_term in normalized_response


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    acceptance = read_jsonl(args.acceptance)
    predictions = read_jsonl(args.predictions)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    threshold = float(config["required_term_threshold"])
    if not 0 <= threshold <= 1:
        raise SystemExit("required_term_threshold must be within [0, 1]")
    if not acceptance:
        raise SystemExit("acceptance set is empty")

    expected_ids = [str(item["id"]) for item in acceptance]
    if len(expected_ids) != len(set(expected_ids)):
        raise SystemExit("acceptance set contains duplicate IDs")
    for item in acceptance:
        required_terms = item.get("required_terms")
        forbidden_terms = item.get("forbidden_terms")
        if (
            not isinstance(required_terms, list)
            or not required_terms
            or len(required_terms) != len(set(required_terms))
            or not isinstance(forbidden_terms, list)
            or len(forbidden_terms) != len(set(forbidden_terms))
        ):
            raise SystemExit(
                f"{item.get('id')}: term lists are invalid or duplicated"
            )
    prediction_by_id: dict[str, str] = {}
    for item in predictions:
        identifier = str(item["id"])
        if identifier in prediction_by_id:
            raise SystemExit(f"duplicate prediction ID: {identifier}")
        prediction_by_id[identifier] = str(item["response"])

    missing = sorted(set(expected_ids) - set(prediction_by_id))
    extra = sorted(set(prediction_by_id) - set(expected_ids))
    if missing or extra:
        raise SystemExit(f"prediction ID mismatch: missing={missing}, extra={extra}")

    per_example = []
    slice_values: dict[str, list[bool]] = defaultdict(list)
    forbidden_hits = 0
    for item in acceptance:
        identifier = str(item["id"])
        response = prediction_by_id[identifier]
        required_terms = [str(term) for term in item["required_terms"]]
        forbidden_terms = [str(term) for term in item["forbidden_terms"]]
        required_found = [
            term for term in required_terms if term_present(term, response)
        ]
        forbidden_found = [
            term for term in forbidden_terms if term_present(term, response)
        ]
        coverage = len(required_found) / len(required_terms)
        passed = coverage >= threshold and not forbidden_found
        slice_name = str(item["slice"])
        slice_values[slice_name].append(passed)
        forbidden_hits += len(forbidden_found)
        per_example.append(
            {
                "id": identifier,
                "slice": slice_name,
                "response": response,
                "required_found": required_found,
                "required_missing": sorted(
                    set(required_terms) - set(required_found)
                ),
                "required_coverage": coverage,
                "forbidden_found": forbidden_found,
                "pass": passed,
                "notes": item["notes"],
            }
        )

    passed_count = sum(item["pass"] for item in per_example)
    payload = {
        "schema_version": 1,
        "contract_name": config["contract_name"],
        "acceptance_sha256": sha256(args.acceptance),
        "evaluation_config_sha256": sha256(args.config),
        "evaluator_sha256": sha256(Path(__file__)),
        "predictions_sha256": sha256(args.predictions),
        "examples": len(per_example),
        "passed": passed_count,
        "overall_pass_rate": passed_count / len(per_example),
        "forbidden_hits": forbidden_hits,
        "slices": {
            name: {
                "examples": len(values),
                "passed": sum(values),
                "pass_rate": sum(values) / len(values),
            }
            for name, values in sorted(slice_values.items())
        },
        "per_example": per_example,
        "metric_limitations": [
            "substring concepts do not establish factual correctness",
            "paraphrases can be false negatives",
            "keyword stuffing can be false positive",
            "human review remains required for generative behavior",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"pass_rate={payload['overall_pass_rate']:.3f} "
        f"forbidden_hits={payload['forbidden_hits']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
