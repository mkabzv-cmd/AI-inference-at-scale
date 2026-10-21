#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase_dir="$(cd "$lesson_dir/.." && pwd)"
index_dir="$phase_dir/41-ingestion-chunks-embeddings-indexes/artifacts/index-a"

cd "$phase_dir/41-ingestion-chunks-embeddings-indexes"
./scripts/run-cpu-lab.sh

cd "$lesson_dir"
mkdir -p artifacts
python3 src/retrieval.py \
  --config configs/retrieval.json \
  --index "$index_dir" \
  evaluate \
  --qrels data/qrels.json \
  --security-cases data/security-cases.json \
  --output artifacts/retrieval-results.json
python3 src/retrieval.py \
  --config configs/retrieval.json \
  --index "$index_dir" \
  query \
  --text "How long are production API credentials valid?" \
  --tenant alpha \
  --method reranked \
  --top-k 8 >artifacts/example-candidates.json
python3 src/failure_analysis.py \
  --results artifacts/retrieval-results.json \
  --qrels data/qrels.json \
  --output artifacts/failure-analysis.json
python3 scripts/verify.py
