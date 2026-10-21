#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l11}"
mkdir -p artifacts

echo "Launching two long requests against a server that admits one generation at a time."
python3 - <<'PY'
import concurrent.futures
import json
import time
import urllib.request
from pathlib import Path

payload = json.loads(Path("requests/chat.json").read_text())
payload["max_tokens"] = 160
body = json.dumps(payload).encode()

def request(index):
    started = time.perf_counter()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/v1/chat/completions",
        data=body,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.load(response)
    return {
        "index": index,
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "server_queue_wait_ms": result["teaching_trace"]["queue_wait_ms"],
    }

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(request, range(2)))
Path("artifacts/serialization-failure.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
print(json.dumps(results, indent=2))
assert max(item["server_queue_wait_ms"] for item in results) > 0
PY

kubectl logs -n "$LAB_NAMESPACE" deployment/transformers-baseline \
  --tail=200 >artifacts/failure-server.log
echo "The queued request is the deliberate limitation, not a Kubernetes failure."
