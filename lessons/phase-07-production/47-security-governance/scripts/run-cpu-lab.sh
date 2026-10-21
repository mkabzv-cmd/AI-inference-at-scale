#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
bundle_dir="$artifact_dir/bundle"

rm -rf -- "$bundle_dir"
mkdir -p "$bundle_dir"
cp "$lesson_dir/fixtures/model-card.json" "$bundle_dir/model-card.json"
cp "$lesson_dir/fixtures/adapter-config.json" "$bundle_dir/adapter-config.json"
cp "$lesson_dir/fixtures/index-manifest.json" "$bundle_dir/index-manifest.json"

python3 "$lesson_dir/src/build_provenance.py" \
  --config "$lesson_dir/configs/bundle.json" \
  --bundle-dir "$bundle_dir" \
  --output "$bundle_dir/provenance.json"

python3 "$lesson_dir/src/verify_provenance.py" \
  --config "$lesson_dir/configs/bundle.json" \
  --provenance "$bundle_dir/provenance.json" \
  --bundle-dir "$bundle_dir"

python3 "$lesson_dir/scripts/verify-k8s-security.py" \
  --manifest "$lesson_dir/k8s/restricted-workload.yaml"

printf 'Security evidence written under %s\n' "$artifact_dir"
