#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_dir"

rm -rf artifacts/index-a artifacts/index-b
python3 src/rag_ingest.py \
  --corpus data/corpus-v1.jsonl \
  --config configs/pipeline.json \
  --output artifacts/index-a
python3 src/rag_ingest.py \
  --corpus data/corpus-v1.jsonl \
  --config configs/pipeline.json \
  --output artifacts/index-b

for generated in documents.jsonl chunks.jsonl vectors.jsonl manifest.json; do
  cmp "artifacts/index-a/$generated" "artifacts/index-b/$generated"
done

python3 src/vector_search.py search \
  --index artifacts/index-a \
  --query "How long do API tokens last?" \
  --tenant alpha \
  --top-k 3 \
  --metric cosine >artifacts/example-search.json
python3 src/vector_search.py benchmark \
  --index artifacts/index-a \
  --queries data/search-queries.json \
  --output artifacts/index-benchmark.json
python3 scripts/verify.py
