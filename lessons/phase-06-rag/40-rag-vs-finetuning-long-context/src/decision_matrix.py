#!/usr/bin/env python3
"""Rank knowledge/adaptation strategies with explicit assumptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def is_score(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= float(value) <= 5
    )


def validate_documents(
    strategy_document: dict, scenario_document: dict
) -> None:
    errors = []
    if strategy_document.get("schema_version") != 1:
        errors.append("strategy schema_version must be 1")
    criteria = strategy_document.get("criteria")
    strategies = strategy_document.get("strategies")
    if (
        not isinstance(criteria, dict)
        or not criteria
        or not all(
            isinstance(name, str)
            and name
            and isinstance(description, str)
            and description
            for name, description in criteria.items()
        )
    ):
        errors.append("criteria must be a non-empty string-to-description object")
        criteria = {}
    if not isinstance(strategies, dict) or not strategies:
        errors.append("strategies must be a non-empty object")
        strategies = {}
    known_requirements = set()
    for name, strategy in strategies.items():
        if not isinstance(name, str) or not name or not isinstance(strategy, dict):
            errors.append("each strategy must have a non-empty name and object value")
            continue
        capabilities = strategy.get("capabilities")
        if not isinstance(capabilities, dict):
            errors.append(f"{name}: capabilities must be an object")
        else:
            missing = sorted(set(criteria) - set(capabilities))
            unknown = sorted(set(capabilities) - set(criteria))
            if missing:
                errors.append(f"{name}: missing criteria: {', '.join(missing)}")
            if unknown:
                errors.append(f"{name}: unknown criteria: {', '.join(unknown)}")
            for criterion, value in capabilities.items():
                if not is_score(value):
                    errors.append(
                        f"{name}.{criterion}: capability must be between 0 and 5"
                    )
        supports = strategy.get("supports")
        if (
            not isinstance(supports, list)
            or not all(isinstance(item, str) and item for item in supports)
            or len(set(supports)) != len(supports)
        ):
            errors.append(f"{name}: supports must be a unique string list")
        else:
            known_requirements.update(supports)

    if scenario_document.get("schema_version") != 1:
        errors.append("scenario schema_version must be 1")
    scenarios = scenario_document.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("scenarios must be a non-empty list")
        scenarios = []
    seen_ids = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("each scenario must be an object")
            continue
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            errors.append("scenario id must be a non-empty string")
            continue
        if scenario_id in seen_ids:
            errors.append(f"{scenario_id}: duplicate scenario id")
        seen_ids.add(scenario_id)
        importance = scenario.get("importance")
        if not isinstance(importance, dict) or not importance:
            errors.append(f"{scenario_id}: importance must be a non-empty object")
            importance = {}
        unknown = sorted(set(importance) - set(criteria))
        if unknown:
            errors.append(
                f"{scenario_id}: unknown criteria: {', '.join(unknown)}"
            )
        for criterion, value in importance.items():
            if not is_score(value):
                errors.append(
                    f"{scenario_id}.{criterion}: importance must be between 0 and 5"
                )
        if importance and all(float(value) == 0 for value in importance.values() if is_score(value)):
            errors.append(f"{scenario_id}: importance must sum above zero")
        hard_requirements = scenario.get("hard_requirements")
        if (
            not isinstance(hard_requirements, list)
            or not all(
                isinstance(item, str) and item for item in hard_requirements
            )
            or len(set(hard_requirements)) != len(hard_requirements)
        ):
            errors.append(
                f"{scenario_id}: hard_requirements must be a unique string list"
            )
        else:
            unknown_requirements = sorted(
                set(hard_requirements) - known_requirements
            )
            if unknown_requirements:
                errors.append(
                    f"{scenario_id}: unknown hard requirements: "
                    + ", ".join(unknown_requirements)
                )
        expected = scenario.get("expected_recommendation")
        if expected is not None and expected not in strategies:
            errors.append(
                f"{scenario_id}: expected_recommendation is not a known strategy"
            )
    if errors:
        raise ValueError("decision input validation failed:\n- " + "\n- ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategies", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    strategy_document = json.loads(
        args.strategies.read_text(encoding="utf-8")
    )
    scenario_document = json.loads(
        args.scenarios.read_text(encoding="utf-8")
    )
    try:
        validate_documents(strategy_document, scenario_document)
    except ValueError as error:
        raise SystemExit(f"ERROR: {error}") from error
    criteria = strategy_document["criteria"]
    strategies = strategy_document["strategies"]
    results = []

    for scenario in scenario_document["scenarios"]:
        total_importance = sum(float(value) for value in scenario["importance"].values())

        rankings = []
        for name, strategy in strategies.items():
            missing_hard = sorted(
                set(scenario["hard_requirements"])
                - set(strategy["supports"])
            )
            contributions = {}
            weighted_total = 0.0
            for criterion, importance in scenario["importance"].items():
                capability = float(strategy["capabilities"][criterion])
                contribution = float(importance) * capability
                contributions[criterion] = {
                    "importance": importance,
                    "capability": capability,
                    "weighted_points": contribution,
                }
                weighted_total += contribution
            score = weighted_total / (total_importance * 5.0)
            rankings.append(
                {
                    "strategy": name,
                    "feasible": not missing_hard,
                    "missing_hard_requirements": missing_hard,
                    "normalized_score": score,
                    "contributions": contributions,
                }
            )

        rankings.sort(
            key=lambda item: (
                not item["feasible"],
                -item["normalized_score"],
                item["strategy"],
            )
        )
        recommendation = next(
            (
                item["strategy"]
                for item in rankings
                if item["feasible"]
            ),
            None,
        )
        results.append(
            {
                "id": scenario["id"],
                "description": scenario["description"],
                "recommendation": recommendation,
                "expected_recommendation": scenario.get(
                    "expected_recommendation"
                ),
                "rankings": rankings,
                "warning": (
                    "Scores expose assumptions; they do not replace a measured "
                    "prototype, risk review, or architecture decision."
                ),
            }
        )

    payload = {
        "schema_version": 1,
        "method": (
            "hard requirements filter first; weighted capability score "
            "breaks ties among feasible strategies"
        ),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(f"{result['id']}: {result['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
