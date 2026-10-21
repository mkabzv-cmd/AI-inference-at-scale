#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase_dir="$(cd "$lesson_dir/.." && pwd)"
lesson41="$phase_dir/41-ingestion-chunks-embeddings-indexes"
lesson42="$phase_dir/42-retrieval-hybrid-reranking"

cd "$lesson42"
./scripts/run-cpu-lab.sh

cd "$lesson_dir"
mkdir -p artifacts
python3 src/grounding.py \
  --index "$lesson41/artifacts/index-a" \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/grounding.json \
  evaluate \
  --questions data/questions.json \
  --output artifacts/grounding-results.json
python3 src/grounding.py \
  --index "$lesson41/artifacts/index-a" \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/grounding.json \
  answer \
  --question "After how many hours do production API tokens expire?" \
  --tenant alpha >artifacts/example-answer.json

python3 src/build_adversarial_corpus.py \
  --base "$lesson41/data/corpus-v1.jsonl" \
  --additional data/adversarial-documents.jsonl \
  --output artifacts/corpus-adversarial.jsonl
python3 "$lesson41/src/rag_ingest.py" \
  --corpus artifacts/corpus-adversarial.jsonl \
  --config "$lesson41/configs/pipeline.json" \
  --output artifacts/adversarial-index
python3 src/security_tests.py \
  --normal-index "$lesson41/artifacts/index-a" \
  --adversarial-index artifacts/adversarial-index \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/grounding.json \
  --forged-answer data/forged-answer.json \
  --output artifacts/security-results.json
python3 scripts/verify.py
