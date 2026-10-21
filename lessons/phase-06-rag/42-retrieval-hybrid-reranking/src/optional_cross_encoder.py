#!/usr/bin/env python3
"""Optionally rerank a recorded candidate list with a pinned cross encoder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    candidate_report = json.loads(args.candidates.read_text())
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as error:
        raise SystemExit(
            "sentence-transformers is not installed; review and install the "
            "optional dependency in an isolated environment"
        ) from error
    model = CrossEncoder(
        config["model_id"],
        revision=config["revision"],
        trust_remote_code=bool(config["trust_remote_code"]),
    )
    pairs = [
        (candidate_report["query"], item["text"])
        for item in candidate_report["results"][: config["candidate_k"]]
    ]
    scores = model.predict(pairs).tolist()
    reranked = [
        {"chunk_id": item["chunk_id"], "score": float(score)}
        for item, score in zip(candidate_report["results"], scores)
    ]
    reranked.sort(key=lambda item: (-item["score"], item["chunk_id"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "model_id": config["model_id"],
                "revision": config["revision"],
                "results": reranked,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"reranked {len(reranked)} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
