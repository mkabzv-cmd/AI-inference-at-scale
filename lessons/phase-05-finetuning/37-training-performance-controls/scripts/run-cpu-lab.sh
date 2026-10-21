#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dataset_lesson="$lesson_root/../33-dataset-engineering-chat-templates"
dataset_manifest="$dataset_lesson/artifacts/dataset/manifest.json"
cd "$lesson_root"
rm -f -- \
  artifacts/study-plan.json \
  artifacts/layout-accounting.json \
  artifacts/fixture-pareto.json
mkdir -p artifacts

if [[ ! -f "$dataset_manifest" ]]; then
  (
    cd "$dataset_lesson"
    ./scripts/run-cpu-lab.sh
  )
fi
python3 src/plan_study.py \
  --config configs/study.json \
  --dataset-manifest "$dataset_manifest" \
  --output artifacts/study-plan.json
python3 src/layout_accounting.py \
  --config configs/layout-lengths.json \
  --output artifacts/layout-accounting.json
python3 src/detect_confounds.py --input fixtures/analyzer-results.json
python3 src/analyze_results.py \
  --input fixtures/analyzer-results.json \
  --output artifacts/fixture-pareto.json
python3 -m json.tool artifacts/study-plan.json >/dev/null
python3 -m json.tool artifacts/layout-accounting.json >/dev/null
python3 -m json.tool artifacts/fixture-pareto.json >/dev/null
printf 'PASS: study arithmetic and analyzer behavior verified on labeled fixtures\n'
