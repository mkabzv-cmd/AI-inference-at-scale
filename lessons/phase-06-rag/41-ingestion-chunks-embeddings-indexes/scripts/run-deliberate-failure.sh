#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_dir"
mkdir -p artifacts

set +e
python3 src/rag_ingest.py \
  --corpus data/corpus-invalid.jsonl \
  --config configs/pipeline.json \
  --output artifacts/invalid-index >artifacts/deliberate-failure.txt 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  echo "FAIL: invalid duplicate/version/license corpus was accepted" >&2
  exit 1
fi
grep -q "duplicate identity" artifacts/deliberate-failure.txt
grep -q "not in the allowlist" artifacts/deliberate-failure.txt
grep -q "semantic version" artifacts/deliberate-failure.txt
echo "PASS: ingestion failed closed on duplicate identity, license, and version defects"
