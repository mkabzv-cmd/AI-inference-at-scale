#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase_dir="$(cd "$lesson_dir/.." && pwd)"
index_dir="$phase_dir/41-ingestion-chunks-embeddings-indexes/artifacts/index-a"
cd "$lesson_dir"
mkdir -p artifacts/failures

expect_rejection() {
  local name="$1"
  shift
  set +e
  "$@" >"artifacts/failures/$name.txt" 2>&1
  local status=$?
  set -e
  if [[ "$status" -eq 0 ]]; then
    echo "FAIL: $name was accepted" >&2
    exit 1
  fi
}

expect_rejection post-filter \
  python3 src/retrieval.py \
    --config configs/invalid-post-filter.json \
    --index "$index_dir" \
    query --text "token" --tenant alpha --method dense
expect_rejection invalid-fusion \
  python3 src/retrieval.py \
    --config configs/invalid-fusion.json \
    --index "$index_dir" \
    query --text "token" --tenant alpha --method hybrid
expect_rejection confounded-qrels \
  python3 src/retrieval.py \
    --config configs/retrieval.json \
    --index "$index_dir" \
    validate-qrels --qrels data/confounded-qrels.json
expect_rejection invalid-top-k \
  python3 src/retrieval.py \
    --config configs/retrieval.json \
    --index "$index_dir" \
    query --text "token" --tenant alpha --method dense --top-k 0

grep -q "before_ranking" artifacts/failures/post-filter.txt
grep -q "RRF" artifacts/failures/invalid-fusion.txt
grep -q "does not match the active corpus" artifacts/failures/confounded-qrels.txt
grep -q "unauthorized" artifacts/failures/confounded-qrels.txt
grep -q "top_k must be a positive integer" artifacts/failures/invalid-top-k.txt
echo "PASS: unsafe filter stage, invalid fusion, invalid top-k, and confounded qrels were rejected"
