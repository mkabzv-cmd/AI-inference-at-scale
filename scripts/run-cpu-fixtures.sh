#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_count=0

run_fixture() {
  lesson_path="$1"
  shift
  fixture_count=$((fixture_count + 1))
  printf '\n[%02d] %s ::' "$fixture_count" "$lesson_path"
  printf ' %q' "$@"
  printf '\n'
  (
    cd "$repo_root/$lesson_path"
    "$@"
  )
}

printf '%s\n' \
  'Running offline curriculum fixtures without third-party Python packages.' \
  'These tests validate teaching mechanics; they do not certify Docker, GPU, Kubernetes, EKS, or cloud execution.'

# Phase 2: the full lesson-12 HTTP benchmark additionally needs its pinned
# httpx dependency, so the no-third-party-Python aggregate begins with lesson
# 16.
run_fixture lessons/phase-02-engines/16-capstone-engine-shootout \
  python3 scripts/cpu-self-test.py

for lesson in \
  17-prefill-decode-memory-accounting \
  18-batching-scheduling-paged-attention \
  19-quantization-systems-tradeoffs \
  20-attention-kernels-compilation-cuda-graphs \
  21-prefix-cache-chunked-prefill-speculative \
  22-disciplined-tuning-workflow \
  23-capstone-optimize-under-slo
do
  run_fixture "lessons/phase-03-optimization/$lesson" \
    ./scripts/run-cpu-lab.sh
done

run_fixture lessons/phase-04-distributed/25-parallelism-taxonomy-arithmetic \
  python3 -m unittest discover -s tests -v
run_fixture lessons/phase-04-distributed/27-nccl-network-characterization \
  ./scripts/test-analyzer.sh
run_fixture lessons/phase-04-distributed/28-toy-model-multinode-mechanics \
  ./scripts/test-arithmetic.sh
run_fixture lessons/phase-04-distributed/30-tensor-vs-pipeline-vs-data \
  ./scripts/test-comparison.sh
run_fixture lessons/phase-04-distributed/31-capstone-distributed-inference-study \
  ./scripts/test-offline.sh

run_fixture lessons/phase-05-finetuning/32-training-computation-graph \
  ./scripts/run-cpu-lab.sh
run_fixture lessons/phase-05-finetuning/33-dataset-engineering-chat-templates \
  ./scripts/run-cpu-lab.sh
run_fixture lessons/phase-05-finetuning/33-dataset-engineering-chat-templates \
  ./scripts/run-deliberate-failure.sh
run_fixture lessons/phase-05-finetuning/34-evaluation-before-optimization \
  ./scripts/run-cpu-baseline.sh
run_fixture lessons/phase-05-finetuning/34-evaluation-before-optimization \
  ./scripts/run-deliberate-failure.sh
for lesson in \
  35-single-gpu-sft \
  36-lora-qlora \
  37-training-performance-controls \
  38-ddp-fsdp2-zero \
  39-capstone-adapt-package-serve
do
  run_fixture "lessons/phase-05-finetuning/$lesson" \
    ./scripts/run-cpu-lab.sh
  run_fixture "lessons/phase-05-finetuning/$lesson" \
    ./scripts/run-deliberate-failure.sh
done

for lesson in \
  40-rag-vs-finetuning-long-context \
  41-ingestion-chunks-embeddings-indexes \
  42-retrieval-hybrid-reranking \
  43-grounded-generation-rag-evaluation-security \
  44-capstone-knowledge-system
do
  run_fixture "lessons/phase-06-rag/$lesson" \
    ./scripts/run-cpu-lab.sh
  run_fixture "lessons/phase-06-rag/$lesson" \
    ./scripts/run-deliberate-failure.sh
done

run_fixture lessons/phase-07-production/45-observability-load-capacity \
  ./scripts/run-local-lab.sh
run_fixture lessons/phase-07-production/45-observability-load-capacity \
  ./scripts/run-deliberate-failure.sh
for lesson in \
  46-autoscaling-reliability \
  47-security-governance
do
  run_fixture "lessons/phase-07-production/$lesson" \
    ./scripts/run-cpu-lab.sh
  run_fixture "lessons/phase-07-production/$lesson" \
    ./scripts/run-deliberate-failure.sh
done
run_fixture lessons/phase-07-production/48-cicd-gitops-reproducibility \
  ./scripts/run-local-pipeline.sh
run_fixture lessons/phase-07-production/48-cicd-gitops-reproducibility \
  ./scripts/run-deliberate-failure.sh
run_fixture lessons/phase-07-production/49-final-capstone-open-model-platform \
  ./scripts/run-local-lab.sh
run_fixture lessons/phase-07-production/49-final-capstone-open-model-platform \
  ./scripts/run-deliberate-failure.sh

printf '\nValidated %d offline fixture command(s) successfully.\n' "$fixture_count"
printf '%s\n' \
  'Generated evidence remains in ignored lesson-level artifacts/ directories for inspection.'
