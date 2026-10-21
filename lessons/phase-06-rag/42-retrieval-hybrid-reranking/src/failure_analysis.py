#!/usr/bin/env python3
"""Extract retrieval misses into an inspectable, machine-readable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = json.loads(args.results.read_text())
    qrels = json.loads(args.qrels.read_text())
    queries = {item["id"]: item for item in qrels["queries"]}
    failures = []
    for method, report in results["methods"].items():
        for case in report["queries"]:
            if case["recall_at_k"] >= 1:
                continue
            query = queries[case["query_id"]]
            missing = sorted(
                set(query["relevance"]) - set(case["ranked_chunk_ids"])
            )
            failures.append(
                {
                    "method": method,
                    "query_id": query["id"],
                    "query": query["text"],
                    "intent": query["intent"],
                    "missing_relevant_chunk_ids": missing,
                    "observed_top_k": case["ranked_chunk_ids"],
                    "diagnosis_prompt": (
                        "Inspect filter, source/chunk, query terms, candidate retrieval, "
                        "fusion, and reranking in that order."
                    ),
                }
            )
    output = {
        "schema_version": 1,
        "failure_count": len(failures),
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"recorded {len(failures)} method/query retrieval misses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
