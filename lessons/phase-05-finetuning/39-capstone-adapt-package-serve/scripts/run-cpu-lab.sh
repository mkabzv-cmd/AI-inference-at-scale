#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase_root="$(cd "$lesson_root/.." && pwd)"
cd "$lesson_root"
rm -rf -- artifacts/fixture-release
rm -f -- artifacts/expected-tamper-failure.txt
mkdir -p artifacts

evaluation_lock_sha="$(
  python3 -c \
    'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
    "$phase_root/34-evaluation-before-optimization/acceptance.lock.json"
)"
release_gates_sha="$(
  python3 -c \
    'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
    "$phase_root/34-evaluation-before-optimization/configs/release-gates.json"
)"
python3 src/build_release.py \
  --config configs/release.json \
  --base-metadata-dir fixtures/base \
  --adapter-dir fixtures/adapter \
  --data-card "$phase_root/33-dataset-engineering-chat-templates/DATA_CARD.md" \
  --model-card MODEL_CARD.template.md \
  --dataset-manifest-sha256 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --training-config-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  --evaluation-lock-sha256 "$evaluation_lock_sha" \
  --release-gates-sha256 "$release_gates_sha" \
  --output artifacts/fixture-release \
  --fixture
python3 src/verify_release.py \
  --release artifacts/fixture-release \
  --allow-fixture
printf 'PASS: nondeployable CPU fixture exercises release hashing and binding\n'
