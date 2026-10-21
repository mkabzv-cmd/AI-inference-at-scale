#!/usr/bin/env python3
"""Optional embedding comparison; downloads nothing unless explicitly executed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise SystemExit(
            "sentence-transformers is not installed; use an isolated environment "
            "and review its dependency lock before running this optional path"
        ) from error
    model = SentenceTransformer(
        config["model_id"],
        revision=config["revision"],
        trust_remote_code=bool(config["trust_remote_code"]),
    )
    chunks = [
        json.loads(line)
        for line in (args.index / "chunks.jsonl").read_text().splitlines()
        if line
    ]
    embeddings = model.encode(
        [chunk["text"] for chunk in chunks],
        normalize_embeddings=bool(config["normalize_embeddings"]),
        show_progress_bar=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        if len(chunks) != len(embeddings):
            raise RuntimeError("embedding output count differs from chunk count")
        for chunk, vector in zip(chunks, embeddings):
            handle.write(
                json.dumps(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "model_id": config["model_id"],
                        "revision": config["revision"],
                        "vector": vector.tolist(),
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )
    print(f"wrote {len(chunks)} optional model embeddings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
