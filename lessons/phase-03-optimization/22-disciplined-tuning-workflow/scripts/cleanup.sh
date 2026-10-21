#!/usr/bin/env bash
set -euo pipefail

for name in oms-l22-b0 oms-l22-e1 oms-l22-e2; do
  docker stop "$name" >/dev/null 2>&1 || true
done
echo "lesson 22 experiment containers removed"
