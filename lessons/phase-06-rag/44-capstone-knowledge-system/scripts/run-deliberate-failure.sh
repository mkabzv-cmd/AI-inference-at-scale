#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$lesson_dir/artifacts/failures"

set +e
IMAGE_REF="example.invalid/knowledge-service:mutable" \
COURSE_NAMESPACE="rag-course" \
"$lesson_dir/scripts/render-k8s.sh" \
  >"$lesson_dir/artifacts/failures/mutable-image.txt" 2>&1
image_status=$?
BASE_IMAGE_REF="python:3.12-slim" \
IMAGE_TAG="knowledge-service:unsafe" \
"$lesson_dir/scripts/build-image.sh" \
  >"$lesson_dir/artifacts/failures/mutable-base.txt" 2>&1
base_status=$?
COURSE_PHASE_DIR="$lesson_dir/.." \
COURSE_CORPUS_RELATIVE="../../../../etc/passwd" \
COURSE_PORT=18081 \
python3 "$lesson_dir/src/service.py" \
  >"$lesson_dir/artifacts/failures/corpus-path-traversal.txt" 2>&1
path_status=$?
COURSE_MODEL_BEARER_TOKEN= \
COURSE_MODEL_CA_BUNDLE= \
python3 "$lesson_dir/src/optional_gpu_study.py" \
  --config "$lesson_dir/configs/optional-gpu-variants.example.json" \
  --questions "$lesson_dir/data/study-questions.json" \
  --output "$lesson_dir/artifacts/should-not-exist.json" \
  --work-dir "$lesson_dir/artifacts/should-not-exist-index" \
  --acknowledge-data-transfer \
  >"$lesson_dir/artifacts/failures/missing-model-auth.txt" 2>&1
auth_status=$?
set -e

if [[ "$image_status" -eq 0 || "$base_status" -eq 0 || "$path_status" -eq 0 || "$auth_status" -eq 0 ]]; then
  echo "FAIL: an unsafe image, corpus path, or model endpoint was accepted" >&2
  exit 1
fi
grep -q "immutable" "$lesson_dir/artifacts/failures/mutable-image.txt"
grep -q "digest pinned" "$lesson_dir/artifacts/failures/mutable-base.txt"
grep -q "must remain inside lesson 41 data" \
  "$lesson_dir/artifacts/failures/corpus-path-traversal.txt"
grep -q "COURSE_MODEL_BEARER_TOKEN" \
  "$lesson_dir/artifacts/failures/missing-model-auth.txt"
echo "PASS: mutable images, escaped corpus paths, and unauthenticated model calls were rejected before external mutation"
