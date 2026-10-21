# 45 — Observability, load, and capacity

**Status:** draft
**Time:** 6–10 hours
**Compute:** `local-cpu` required; optional `g1` or `g3`
**GPU budget:** zero for the simulator; define a bounded budget before a real run
**Prerequisites:** 12, 17, 18, 23, 44
**Last reviewed:** 2026-10-21

## Why this matters

A user says, “The model is slow.” That symptom can originate in admission,
networking, retrieval, a request queue, tokenization, prefill, decode, KV-cache
pressure, GPU kernels, CPU throttling, storage, Kubernetes scheduling, node
provisioning, or another tenant. Looking only at GPU utilization cannot identify
the layer.

Production observability must let an operator move from one request to the
correlated evidence:

```text
request ID / trace ID
  -> gateway span
  -> retrieval span
  -> model queue
  -> prefill / time to first token
  -> decode / inter-token latency
  -> completion
  -> engine, GPU, Pod, and node state
```

This lesson uses a local model-server simulator so you can create a real
saturation curve without GPU cost. The server has two model slots. Each request
spends a small fixed time in simulated prefill and per-token decode. Above two
concurrent requests, work waits on a semaphore. The load generator sends 42
requests across four concurrency stages, propagates request and trace IDs, and
records queue time, time to first token (TTFT), inter-token latency (ITL), total
latency, status, and token counts.

The simulator does not predict vLLM, SGLang, llama.cpp, or your model. It teaches
the measurement chain. You will then map the same schema to an actual
Phase-2/3/4 deployment, adding engine metrics and NVIDIA DCGM telemetry instead
of replacing the client evidence.

## Learning outcomes

By the end, you can:

- distinguish logs, metrics, and traces and explain why all three are useful;
- propagate a request ID and W3C trace context across service boundaries;
- distinguish end-to-end latency, queue time, TTFT, ITL, and token throughput;
- explain why TTFT usually includes queueing and prefill while ITL reflects
  decode cadence;
- build a stepped-concurrency experiment instead of an uncontrolled stress
  test;
- calculate p50 and p95 from raw request records;
- identify a first SLO breach and correlate it with queue growth;
- distinguish saturation, throughput plateau, errors, and latency inflation;
- map service evidence to engine scheduler, KV cache, GPU, Pod, and node
  evidence;
- design low-cardinality metrics and retain high-cardinality request identity
  in logs/traces;
- produce a capacity statement with workload, model, runtime, quality, and
  hardware boundaries.

## What you will build

The required path builds and runs:

- a standard-library HTTP model simulator with two active slots;
- health, readiness, OpenAI-style completion, and Prometheus metrics endpoints;
- structured server completion logs;
- a concurrent step-load generator;
- a capacity analyzer that applies the checked-in SLO;
- a verifier requiring exact client/server request correlation;
- Prometheus recording/alert rules;
- an OpenTelemetry Collector teaching configuration;
- a starter dashboard with queue, in-flight, capacity, and error panels.

The local fixture should show a passing low-concurrency baseline and an SLO
breach at higher concurrency as queue time enters TTFT. Exact timings vary by
host. The verifier checks robust properties, not copied milliseconds.

For the optional path, point the load generator at a private real endpoint,
replace simulator-only response headers with client-side streaming timestamps
and engine metrics, then retain the same stage and evidence discipline.

## Files in this lesson

```text
45-observability-load-capacity/
├── README.md
├── configs/
│   └── load-plan.json
├── observability/
│   ├── dashboard.json
│   ├── otel-collector.yaml
│   └── prometheus-rules.yaml
├── results.schema.json
├── scripts/
│   ├── run-deliberate-failure.sh
│   ├── run-local-lab.sh
│   ├── stop-local-server.sh
│   └── verify.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── analyze_capacity.py
    ├── fake_model_server.py
    └── load_generator.py
```

All generated evidence is placed beneath ignored `artifacts/`.

## Under the hood

### Request identity and trace context

The client creates a unique request ID and a 32-hex-character trace ID. It sends
the request ID in `X-Request-ID` and a W3C-style `traceparent`:

```text
00-<32 hex trace id>-<16 hex span id>-01
```

The server logs and returns the IDs. The lesson verifier requires the set of
client request IDs to equal the set of server completion IDs. In a multi-service
system, each service creates child spans while retaining the trace ID.

Request IDs are high cardinality. Do not use them as Prometheus labels: one time
series per request can exhaust the metrics system. Put request identity in
structured logs and traces. Metrics aggregate stable dimensions such as route,
model, status class, region, and bounded configuration—not prompt text, user
ID, or arbitrary model IDs.

### TTFT, ITL, and end-to-end time

For a streaming request:

```text
client sends request
  |-- network/admission/retrieval/queue/prefill --| first token
                                                  |-- decode gaps --| last token
```

TTFT is elapsed time from the chosen client start to the first output token.
State the measurement boundary. Server-side TTFT may exclude client network
time. End-to-end client TTFT includes it.

ITL describes gaps between output tokens, often summarized by mean or
percentiles. Averaging a whole response into `decode duration / token count`
can hide bursts and stalls; a streaming client should timestamp each token or
chunk. Non-streaming total latency cannot reveal TTFT and ITL separately.

The simulator reports headers so the mechanism remains dependency-free. A real
run must timestamp the response stream and verify how the engine defines its
metrics.

### Queueing and Little's Law

At steady state, Little's Law relates average in-system work:

```text
L = λW
```

`L` is average concurrent work, `λ` throughput, and `W` average time in the
system. It is a consistency tool, not a promise under changing load. When
arrival demand exceeds sustainable service rate, a queue grows. Throughput may
plateau while tail latency rises dramatically.

The simulator has two active slots. Concurrency above two initially increases
slot utilization, but eventually adds waiting rather than service capacity.
This is intentionally visible in queue and p95 TTFT.

### Prefill and decode evidence

Prefill processes prompt tokens, typically exposing parallel compute and memory
bandwidth differently from one-token-at-a-time decode. Decode holds per-request
KV cache and repeatedly schedules active sequences. Workload shape matters:

- prompt length distribution;
- requested and actual output length;
- arrival pattern;
- concurrent requests;
- cache hit/miss behavior;
- sampling parameters;
- model/quantization/parallel layout.

“Requests per second” without those dimensions is not transferable capacity.
Record prompt and completion tokens, then report token throughput alongside
request throughput.

### Engine, GPU, Pod, and node layers

A real dashboard should correlate:

- client error/latency and request rate;
- request queue and active/running/waiting sequences;
- prefill and decode token rates;
- KV cache use, eviction, and allocation failures;
- batch size and scheduler decisions;
- GPU utilization, memory, power, clocks, errors, and interconnect/network;
- container CPU, throttling, memory, restarts, and filesystem;
- Pod readiness, scheduling, termination, and node condition;
- model/index/cache load state.

Metric names differ by engine and version. Inspect `/metrics` and the installed
DCGM exporter. Never write a dashboard query from a blog, see an empty graph,
and interpret “no data” as zero.

### Percentiles and coordinated omission

The analyzer calculates a nearest-rank percentile from raw records. Small stage
counts make tail percentiles coarse. Real studies need more samples, warmup,
confidence/variance reporting, and a defined aggregation window.

A closed-loop worker that sends the next request only after the previous one
completes can under-represent overload: the client slows its own arrival rate
when the service slows. This lesson is a controlled concurrency test, not an
open-loop arrival-rate benchmark. Lesson 12's methodology still applies.

## Prerequisites and preflight

Run from the lesson directory:

```bash
cd lessons/phase-07-production/45-observability-load-capacity
python3 --version
curl --version | head -n 1
python3 -m json.tool configs/load-plan.json >/dev/null
```

Confirm that the port is unused:

```bash
export OMS_PORT=8045
if curl -fs "http://127.0.0.1:$OMS_PORT/healthz" >/dev/null 2>&1; then
  echo "Choose another OMS_PORT; a service is already listening"
  exit 1
fi
```

Read the SLO and stage sizes:

```bash
python3 - <<'PY'
import json
from pathlib import Path

plan = json.loads(Path("configs/load-plan.json").read_text())
print("SLO", plan["slo"])
for stage in plan["stages"]:
    print(stage)
PY
```

For an optional GPU run, first complete the target engine's own preflight,
record image/model/tokenizer revisions, confirm the Service is private, verify
GPU capacity and cost, and save idle baseline telemetry.

## Cost and safety

The required path uses localhost and CPU for a few seconds.

Load testing is authorized traffic only. Never point this generator at a
production, public, third-party, or metered endpoint without explicit approval,
a traffic budget, rate limits, and a stop condition. The supplied plan is
bounded to 42 requests but can still be inappropriate for another system.

Prometheus metrics and traces can leak model names, internal topology, tenant
labels, prompt sizes, request timing, or response content. Do not log prompts
or generated text by default. Apply retention and access controls.

For GPU experiments, record the original node-group capacity and restore it.
Stop immediately on uncontrolled errors, public exposure, unexpected scale-out,
or missing telemetry.

## Predict before running

Create `artifacts/predictions.md`:

1. At what concurrency should queueing first appear with two active slots?
2. Which should rise first in the simulator: ITL or TTFT?
3. Will throughput keep doubling from concurrency two to four to eight?
4. Why can GPU utilization remain high while latency becomes unacceptable?
5. Why should request IDs not be Prometheus labels?
6. Which client/server IDs must match for the trace to be useful?
7. Does a p95 from six requests estimate a production tail reliably?
8. Which real engine and DCGM metrics would distinguish scheduler saturation
   from CPU throttling or network delay?

Do not edit the predictions after the run.

## Lab outline

1. Inspect the load plan and simulator capacity.
2. Start the service and run four concurrency stages.
3. Capture raw client records, server logs, and metrics.
4. Aggregate throughput, queue, TTFT, and total latency.
5. Identify the first SLO breach.
6. Join a request across client and server evidence.
7. Deliberately destroy correlation and verify rejection.
8. Map the same evidence contract to a real model endpoint.

## Step-by-step lab

### 1. Run the local experiment

```bash
chmod +x scripts/*.sh
./scripts/run-local-lab.sh
```

Expected shape:

```text
stage=c1 concurrency=1 requests=6
...
c1 rps=<value> p95_ttft=<value> slo_pass=True
...
first_slo_breach=<higher-concurrency stage>
PASS: 42 requests correlate across client/server evidence ...
```

The helper starts the server, waits for readiness, runs load, scrapes metrics,
analyzes results, verifies them, and stops the server with a shell trap.

### 2. Inspect raw evidence before charts

```bash
sed -n '1,3p' artifacts/requests.ndjson
sed -n '1,3p' artifacts/server.ndjson
cat artifacts/metrics.prom
```

Pick one request ID:

```bash
request_id="$(
  python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("artifacts/requests.ndjson").read_text().splitlines()[0])["request_id"])
PY
)"
grep -F "$request_id" artifacts/requests.ndjson
grep -F "$request_id" artifacts/server.ndjson
```

Compare client total with server total. Small differences represent HTTP and
client overhead; the simulator runs locally, so do not generalize the delta.

### 3. Read the saturation curve

```bash
python3 -m json.tool artifacts/capacity-report.json
```

Create a compact table:

```bash
python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("artifacts/capacity-report.json").read_text())
print("stage c rps p95_queue p95_ttft pass")
for row in report["stages"]:
    print(
        row["stage"],
        row["concurrency"],
        f"{row['requests_per_second']:.2f}",
        f"{row['p95_queue_seconds']:.3f}",
        f"{row['p95_ttft_seconds']:.3f}",
        row["slo_pass"],
    )
PY
```

Explain the first breach from raw queue records. Do not call a stage “capacity”
merely because it is the last passing point; sample size and workload scope
matter. A useful statement is:

> Under this exact simulator, plan, host, and SLO, the low stages passed while
> a higher stage breached p95 TTFT as queue time grew.

### 4. Inspect observability assets

```bash
python3 -m json.tool observability/dashboard.json >/dev/null
sed -n '1,240p' observability/prometheus-rules.yaml
sed -n '1,200p' observability/otel-collector.yaml
```

The dashboard intentionally leaves engine/GPU queries blank. Fill them only
after inspecting real metric names and labels.

### 5. Adapt to a real endpoint

Use a copy of the load plan under artifacts. Lower request counts first. Extend
the client to stream and timestamp the first and every subsequent token. Record:

- endpoint route and private access method;
- engine/version/image digest;
- model/tokenizer/revision/quantization;
- tensor/pipeline parallel settings;
- scheduler/cache flags;
- hardware and node count;
- warm/cold state;
- exact workload distribution;
- engine and DCGM metrics scrape.

Do not compare the simulator numbers with GPU results as if they were the same
system.

## Deliberate failure

Run the normal lab first, then:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-correlation-failure.txt
```

The script changes one client request ID while leaving the server log intact.
Aggregate latency remains plausible, but the verifier rejects the evidence
because one request can no longer be joined.

Recovery is to regenerate evidence from the source request, not to edit the
server log to match:

```bash
./scripts/run-local-lab.sh
```

As an additional drill, stop the simulator during a stage and confirm that
errors remain individual records rather than disappearing from the denominator.
Restore the normal lab before completing the lesson.

## Verification

Run:

```bash
./scripts/run-local-lab.sh
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/capacity-report.json >/dev/null
python3 -m json.tool observability/dashboard.json >/dev/null
```

Verify totals manually:

```bash
python3 - <<'PY'
import json
from pathlib import Path

client = [
    json.loads(line)
    for line in Path("artifacts/requests.ndjson").read_text().splitlines()
]
server = [
    json.loads(line)
    for line in Path("artifacts/server.ndjson").read_text().splitlines()
]
assert len(client) == len(server) == 42
assert {r["request_id"] for r in client} == {r["request_id"] for r in server}
assert all(r["status"] == 200 for r in client)
print("PASS: raw evidence is complete and correlatable")
PY
```

A real GPU study also requires a correctness/quality check from earlier phases.
Higher token throughput is not acceptable if outputs or retrieval quality
regress.

## Troubleshooting

If the port is occupied, set a different `OMS_PORT`. Do not kill an unidentified
process.

If readiness never succeeds, inspect `artifacts/server.stdout.log` and verify
the local Python can bind to loopback.

If the first stage breaches, the host may be heavily loaded or the timing
threshold may not fit the environment. Preserve the raw result. Repeat from an
idle host before changing the SLO; do not relax it solely to make the test pass.

If no high stage breaches, verify simulator capacity is two and that requests
overlap. Host scheduling can alter exact boundaries, but p95 queue at the final
stage should be visibly nonzero.

If JSON contains `NaN`, a request likely failed before server timing headers
arrived. Inspect status/error and make the analyzer explicitly handle failures
before using that result in a published report.

If Prometheus queries return no series, scrape `/metrics`, inspect target health,
then inspect actual names/labels. Empty is unknown, not healthy.

If `nvidia-smi` utilization is low during a real test, correlate CPU
tokenization, request arrival, batch formation, model load, and engine logs
before declaring the GPU too large.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── server.stdout.log
├── server.ndjson
├── requests.ndjson
├── requests.metadata.json
├── metrics.prom
├── capacity-report.json
├── expected-correlation-failure.txt
├── dashboard-export.json
├── real-environment.json
├── real-engine-metrics.prom
├── real-dcgm-metrics.prom
└── report.md
```

`report.md` must include:

- SLO and workload;
- model/runtime/hardware identity;
- warmup and cache state;
- raw sample counts and errors;
- p50/p95 queue, TTFT, ITL, total, request/s, and token/s;
- first and second suspected bottlenecks;
- correlated request/trace example;
- quality gate;
- limitations and cost;
- safe capacity recommendation and headroom.

## Exercises

1. Add a true streaming response and timestamp every chunk.
2. Add an open-loop arrival-rate generator and demonstrate coordinated
   omission in the closed-loop test.
3. Calculate Little's Law estimates from each steady stage and explain
   deviations.
4. Add prompt-length stages while holding concurrency fixed.
5. Add output-length stages and compare TTFT with total latency.
6. Create a Prometheus histogram with justified buckets for TTFT and explain
   aggregation constraints.
7. Add retrieval latency and a child span to the fake server.
8. Add bounded model/config labels and prove prompt text never becomes a metric
   label.
9. Map exact vLLM or SGLang metrics from the version used in Phase 2.
10. Correlate GPU power and memory with prefill/decode stages on `g1`.
11. Compare one model replica with three data-parallel replicas using the same
    arrival process.
12. Write a capacity plan that includes failure headroom rather than operating
    at the last passing stage.

## Completion gate

You are done when:

- all local scripts and the deliberate failure pass;
- 42 client records join exactly to 42 server completions;
- low concurrency passes and higher concurrency exposes an SLO boundary;
- you can explain queue, TTFT, ITL, total latency, request throughput, and token
  throughput;
- your dashboard does not invent engine metric names;
- you can diagnose the simulator without entering its process;
- any real GPU result includes quality, model, engine, hardware, workload,
  telemetry, cost, and cleanup evidence;
- your capacity statement is scoped to the measured configuration.

## Cleanup

Stop any leftover local process safely:

```bash
./scripts/stop-local-server.sh
rm -rf -- artifacts
test ! -e artifacts
```

For a Kubernetes/GPU run, stop the load source first, remove only the lesson
workload/telemetry objects, verify Services and volumes are gone, and restore
the GPU node group to its saved starting capacity. Confirm no load balancer or
chargeable telemetry workspace was created unintentionally.

## Primary references

Sources were reviewed on 2026-10-21:

- [OpenTelemetry tracing concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Prometheus metric and label naming](https://prometheus.io/docs/practices/naming/)
- [Prometheus histograms and summaries](https://prometheus.io/docs/practices/histograms/)
- [NVIDIA DCGM Exporter](https://github.com/NVIDIA/dcgm-exporter)
- [Kubernetes resource metrics pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- [The Tail at Scale](https://research.google/pubs/the-tail-at-scale/)

The local simulator path is author-validated. No real GPU, engine, Prometheus,
OpenTelemetry backend, or Kubernetes deployment was run as part of this draft.
