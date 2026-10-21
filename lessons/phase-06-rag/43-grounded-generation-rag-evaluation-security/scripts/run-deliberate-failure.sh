#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase_dir="$(cd "$lesson_dir/.." && pwd)"
lesson41="$phase_dir/41-ingestion-chunks-embeddings-indexes"
lesson42="$phase_dir/42-retrieval-hybrid-reranking"
cd "$lesson_dir"
mkdir -p artifacts/failures

set +e
python3 src/grounding.py \
  --index "$lesson41/artifacts/index-a" \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/unsafe-allow-injection.json \
  answer --question "What should I ignore?" --tenant alpha \
  >artifacts/failures/unsafe-grounding.txt 2>&1
unsafe_status=$?
python3 src/grounding.py \
  --index "$lesson41/artifacts/index-a" \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/grounding.json \
  validate-answer --answer data/forged-answer.json \
  >artifacts/failures/forged-answer.txt 2>&1
forged_status=$?
python3 src/grounding.py \
  --index "$lesson41/artifacts/index-a" \
  --retrieval-config "$lesson42/configs/retrieval.json" \
  --grounding-config configs/grounding.json \
  evaluate \
  --questions data/confounded-questions.json \
  --output artifacts/should-not-exist.json \
  >artifacts/failures/confounded-questions.txt 2>&1
questions_status=$?
python3 src/openai_compatible_client.py \
  --config configs/unsafe-remote-model-endpoint.json \
  --grounded-request data/forged-answer.json \
  --output artifacts/should-not-exist-model-response.json \
  >artifacts/failures/unsafe-model-endpoint.txt 2>&1
endpoint_status=$?
set -e

if [[ "$unsafe_status" -eq 0 || "$forged_status" -eq 0 || "$questions_status" -eq 0 || "$endpoint_status" -eq 0 ]]; then
  echo "FAIL: unsafe grounding, citation, evaluation, or endpoint input was accepted" >&2
  exit 1
fi
grep -q "must be block_chunk" artifacts/failures/unsafe-grounding.txt
grep -q "unknown citation" artifacts/failures/forged-answer.txt
grep -q "does not match the active corpus" artifacts/failures/confounded-questions.txt
grep -q "unauthorized for beta" artifacts/failures/confounded-questions.txt
grep -q "numeric IPv4 loopback" artifacts/failures/unsafe-model-endpoint.txt
echo "PASS: fail-open injection handling, forged citations, confounded questions, and unsafe model endpoints were rejected"
