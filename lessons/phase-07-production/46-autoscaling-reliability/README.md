# 46 — Autoscaling and reliability

**Status:** draft
**Time:** 8–14 hours
**Compute:** `local-cpu` required; optional bounded `g1` or `g3`
**GPU budget:** zero for simulation; declare a maximum replica-minutes for EKS
**Prerequisites:** 45
**Last reviewed:** 2026-10-21

## Why this matters

A conventional stateless web server may start in seconds and scale reasonably
from CPU. A model Pod can wait for a GPU node, pull a large image, download or
mount weights, allocate device memory, compile kernels, capture graphs, warm
caches, and only then become ready. Adding replicas after an overload begins
does not erase that cold-start interval.

GPU inference also has demand signals that container CPU does not describe. A
model can have a growing request queue, full KV cache, saturated batch
scheduler, or unacceptable TTFT while its CPU metric remains below an HPA
target. Conversely, high GPU utilization can be healthy if queues and latency
remain within the service objective.

This lesson separates four control loops:

```text
request demand
  -> admission/backpressure
  -> Pod autoscaler desired replicas
  -> scheduler Pending Pods
  -> node provisioning / GPU registration
  -> image + model load
  -> readiness
  -> usable serving capacity
```

The required CPU simulation compares static capacity, an intentionally
misleading CPU signal, and a queue-aware signal. It models a bounded queue,
rejection, loading replicas, scale limits, cooldown, scale-down delay, and
wait-time SLO. The Kubernetes path supplies guarded HPA and KEDA examples,
graceful drain hooks, probes, a PodDisruptionBudget (PDB), immutable image
rendering, and a targeted Pod failure drill.

## Learning outcomes

By the end, you can:

- choose a scaling signal from measured saturation evidence;
- explain why Pod scaling and GPU node provisioning are separate controllers;
- trace desired replicas through scheduling, node launch, model load, and
  readiness;
- calculate how cold start changes the capacity lead time;
- distinguish queue length, arrival rate, concurrency, latency, utilization,
  and KV-cache pressure;
- apply min/max bounds, rate limits, cooldown, and scale-down stabilization;
- design admission, bounded queues, timeouts, and overload rejection;
- explain graceful drain, readiness removal, termination grace, and in-flight
  completion;
- use a PDB without assuming it protects against every voluntary or involuntary
  failure;
- inject a scoped Pod failure and evaluate bounded degradation;
- plan node interruption, Spot, and rollout recovery without claiming zero
  request loss;
- prove that load stopped and GPU capacity returned to its starting state.

## What you will build

The local lab simulates 24 ten-second demand steps with one conceptual model
Pod initially ready. Each ready Pod serves four requests per step. A burst
arrives faster than one Pod can serve, and the queue is capped at 32.

You will compare:

- `static`: one Pod throughout;
- `cpu`: a 35% CPU signal against a 70% target, so it does not see model
  backlog;
- `queue`: desired replicas derived from queued requests, bounded at four,
  with a three-step cold start and stabilized scale-down.

The output contains every timeline step, completed/rejected requests, wait
percentiles, peak ready/loading Pods, and scale actions. The verifier requires
queue-aware scaling to add capacity, reduce rejection and p95 waiting, satisfy
the authored SLO, and outperform the static/CPU paths.

The deliberate simulation removes cooldown/stabilization and uses alternating
demand. It must exceed a scale-action budget.

The optional Kubernetes path renders:

- a digest-pinned one-GPU Deployment and private ClusterIP Service;
- startup/readiness/liveness probes;
- a drain request plus termination grace;
- a PDB;
- either a custom Pods-metric HPA or a Prometheus-backed KEDA `ScaledObject`;
- a bounded one-Pod-per-interval scale policy and slow scale-down.

Do not apply HPA and KEDA to the same target simultaneously.

## Files in this lesson

```text
46-autoscaling-reliability/
├── README.md
├── configs/
│   ├── simulation.json
│   └── unstable-simulation.json
├── k8s/
│   ├── broken-cpu-hpa.yaml
│   ├── hpa-custom-metric.yaml.tpl
│   ├── keda-scaledobject.yaml.tpl
│   └── workload.yaml.tpl
├── results.schema.json
├── scripts/
│   ├── check-autoscaling-manifest.py
│   ├── inject-pod-failure.sh
│   ├── render-manifests.sh
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   ├── verify.py
│   └── verify_stability.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    └── autoscaling_simulator.py
```

Generated studies and rendered manifests go under ignored `artifacts/`.

## Under the hood

### From metric to ready capacity

An HPA computes desired Pod replicas. It does not create an EC2 instance. If no
node has an allocatable GPU, the new Pod remains Pending. A managed node-group
autoscaler or Karpenter-like provisioner must observe unschedulable demand,
choose an instance type/subnet/AZ, launch it, wait for bootstrap and cluster
join, and expose `nvidia.com/gpu` through the driver/device-plugin path.

Then the Pod pulls the image and obtains model artifacts. The engine allocates
weights and cache, initializes, and passes readiness. Only then does the Service
send it traffic.

Capacity lead time is therefore approximately:

```text
metric collection + autoscaler reaction
+ Pod scheduling / node provisioning
+ image and model artifact availability
+ engine initialization and warmup
+ readiness propagation
```

Measure each interval. A scale decision that looks fast in the HPA log may take
many minutes to produce a ready GPU replica.

### Signal selection

CPU can be useful when preprocessing is the bottleneck, but it is not a generic
GPU-demand signal. Candidate signals include:

- queued requests per ready Pod;
- waiting sequences or scheduler backlog;
- arrival rate relative to measured service rate;
- active sequences/KV-cache occupancy;
- deadline or p95 TTFT error;
- token backlog rather than request count;
- a composite with readiness and available node capacity.

Latency is close to the user objective but reactive and noisy. Queue is an early
signal but must be normalized to workload size: one long prompt can represent
more work than many short prompts. The right metric follows the first
saturation mechanism measured in lesson 45.

### Desired replicas

The teaching simulator uses:

```text
desired = ceil(queue depth / queue target per Pod)
desired = clamp(min replicas, desired, max replicas)
```

This is intentionally simple. KEDA's Prometheus trigger and an HPA external or
Pods metric apply their own formulas. Confirm whether the metric is total,
average, per-Pod, or rate. A total queue compared against an average target can
over- or under-scale if semantics are mismatched.

### Backpressure

During cold start, demand may exceed service rate even after a correct scale
decision. An unbounded queue converts overload into unbounded memory and
latency. Use:

- bounded admission;
- request deadlines;
- maximum prompt/output lengths;
- per-tenant quotas;
- explicit 429/503 with retry guidance;
- upstream circuit breaking;
- cancellation propagation;
- priority only with a clear starvation policy.

Rejected work is not “autoscaler failure” if rejection protects a documented
latency and cost envelope. It must be measured and communicated.

### Scale stability and cost

Fast scale-up can protect latency but may launch expensive replicas for a brief
spike. Fast scale-down can kill warmed capacity and create oscillation. The
provided policies add at most one Pod per minute and wait ten minutes before
scale-down. These are teaching values, not universal settings.

Define:

- maximum replicas and node types;
- maximum replica-GPU-minutes per experiment;
- stabilization and cooldown;
- fallback when metrics disappear;
- behavior when the node quota or capacity market cannot satisfy demand.

KEDA's fallback in the template keeps one replica when the metric source fails.
Whether fail-open, fail-closed, or fixed fallback is correct depends on service
criticality, cost, and exposure.

### Readiness, drain, and termination

Before terminating, stop new traffic by failing/removing readiness, tell the
engine to drain, allow endpoint propagation, and wait for in-flight requests
within a bounded grace period. The template calls `/drain` and sleeps before
termination. The actual engine must implement and verify that contract.

A `preStop` sleep without a functioning drain endpoint merely delays
termination. A long `terminationGracePeriodSeconds` does not guarantee clients
wait or retry safely.

### Failure classes

A PDB affects voluntary disruptions such as some node drains. It does not
prevent process crashes, hardware loss, Spot interruption, AZ failure, forced
deletion, or every rollout configuration. The template uses `minAvailable: 1`,
which blocks a voluntary eviction while only one replica is healthy; it cannot
create redundancy. Use availability requirements to choose replica count and
topology.

## Prerequisites and preflight

Run locally:

```bash
cd lessons/phase-07-production/46-autoscaling-reliability
python3 --version
python3 -m json.tool configs/simulation.json >/dev/null
```

Inspect bounds and cold start:

```bash
python3 - <<'PY'
import json
from pathlib import Path

config = json.loads(Path("configs/simulation.json").read_text())
for key in (
    "minimum_pods",
    "maximum_pods",
    "cold_start_steps",
    "maximum_queue",
    "queue_target_per_pod",
):
    print(key, config[key])
print("SLO", config["slo"])
PY
```

For Kubernetes, verify context and installed controllers without mutating:

```bash
kubectl config current-context
kubectl auth can-i create horizontalpodautoscalers.autoscaling \
  --namespace "<dedicated-lab-namespace>"
kubectl api-resources | grep -E 'HorizontalPodAutoscaler|ScaledObject'
```

KEDA is optional. A custom HPA metric requires a working metrics adapter. Do not
apply either manifest until the queue metric exists and you understand its
semantics.

## Cost and safety

The CPU simulation is free.

The Kubernetes template can scale to four GPUs. That ceiling may still be
unaffordable. Lower it before applying if your approved budget is smaller.
Record:

```text
maximum cost ≈ maximum GPU nodes × price per node-hour × test hours
```

Also include model storage, image transfer, telemetry, and load generation.
Confirm the exact cluster, region, namespace, model image digest, current
replicas, and node-group starting capacity. The render script accepts only a
lesson-prefixed namespace, a digest image, and a private `.svc` Prometheus URL.

Failure injection is scoped to one labeled Pod in the confirmed namespace.
Never run it against a shared or production service. Stop if the autoscaler
exceeds the declared cap or metrics disappear.

## Predict before running

Write `artifacts/predictions.md`:

1. Will the simulated CPU HPA differ from static capacity?
2. How many steps pass before a requested queue-scaled Pod becomes ready?
3. Can a correct scale decision prevent every rejection during cold start?
4. Which strategy should have lower p95 wait and why?
5. What happens if queue target is zero?
6. Why can no scale-down delay cause oscillation?
7. Which controller creates Pods and which creates GPU nodes?
8. What must happen before a terminating Pod stops receiving new traffic?
9. Does a PDB protect against Spot loss?
10. What is your maximum acceptable GPU-minutes for the optional test?

Preserve predictions.

## Lab outline

1. Run static, CPU, and queue demand simulations.
2. Compare timelines, rejection, waiting, and scale actions.
3. Trace one requested Pod through its loading interval.
4. Remove stabilization and detect oscillation.
5. Reject the deliberately unsafe CPU-only HPA.
6. Render digest-pinned bounded manifests.
7. Optionally deploy one autoscaler and run controlled load.
8. Inject one Pod failure and measure recovery.
9. Stop load and prove capacity cleanup.

## Step-by-step lab

### 1. Run the controller simulation

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected shape:

```text
static rejected=<high> p95_wait_steps=<high> scale_actions=0 peak_ready=1
cpu rejected=<same> p95_wait_steps=<same> scale_actions=0 peak_ready=1
queue rejected=<lower> p95_wait_steps=<lower> scale_actions=<positive> peak_ready=4
PASS: the CPU signal misses demand ...
```

Exact values are deterministic for this simulation. Treat them as fixture
results, not real capacity.

### 2. Inspect the timeline

```bash
python3 - <<'PY'
import json
from pathlib import Path

study = json.loads(Path("artifacts/scaling-study.json").read_text())
queue = next(r for r in study["results"] if r["strategy"] == "queue")
for row in queue["timeline"]:
    if row["arrivals"] >= 18 or row["loading_pods"]:
        print(row)
PY
```

Identify the first scale request, loading interval, first additional ready Pod,
peak queue, and start of scale-down. Convert wait steps to seconds with the
recorded step duration.

### 3. Run the instability drill

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-stability-failure.txt
```

The alternating demand fixture has no cooldown or scale-down delay. It exceeds
the allowed scale-action budget. Recovery means adding stabilization based on
measured burst duration and cold start, not merely increasing the action budget.

### 4. Inspect and reject the bad HPA

```bash
set +e
python3 scripts/check-autoscaling-manifest.py \
  --manifest k8s/broken-cpu-hpa.yaml
status=$?
set -e
test "$status" -ne 0
```

It should identify CPU-only demand, a cost ceiling violation, and missing
behavior controls.

### 5. Render safe templates

Use local placeholders for static inspection:

```bash
export LAB_NAMESPACE="oms-lesson-46-test"
export MODEL_IMAGE="example.invalid/model@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
export PROMETHEUS_URL="http://prometheus.monitoring.svc:9090"
./scripts/render-manifests.sh

python3 scripts/check-autoscaling-manifest.py \
  --manifest artifacts/rendered/hpa-custom-metric.yaml
```

Before a live run, replace placeholders with your private digest and in-cluster
metric endpoint. Apply the workload plus exactly one of HPA or KEDA:

```bash
kubectl apply -f artifacts/rendered/workload.yaml
kubectl apply -f artifacts/rendered/hpa-custom-metric.yaml
```

Observe:

```bash
kubectl get deploy,pod,hpa,pdb -n "$LAB_NAMESPACE" -w
kubectl describe hpa oms-model -n "$LAB_NAMESPACE"
kubectl get events -n "$LAB_NAMESPACE" --sort-by=.lastTimestamp
```

Capture queue, desired/ready replicas, Pending time, node appearance, image/model
load, readiness, errors, and latency on one timeline.

### 6. Optional failure injection

Only after confirming namespace and bounded load:

```bash
export CONFIRM_NAMESPACE="$LAB_NAMESPACE"
./scripts/inject-pod-failure.sh
```

Verify the Service stops routing to the deleted endpoint, a replacement appears,
the model becomes ready, and queued/rejected/client-timeout behavior matches
your reliability objective.

## Deliberate failure

The required deliberate failure is the oscillating simulation:

```bash
./scripts/run-deliberate-failure.sh
```

The optional live failures are:

1. delete one confirmed lesson Pod;
2. remove the metric adapter or point KEDA at a nonexistent metric only in a
   disposable namespace;
3. send demand while no GPU node is ready and observe the cold-start gap.

Do not simulate Spot interruption by terminating an unidentified instance.
Use an approved, precisely targeted lab mechanism and retain interruption,
drain, reschedule, and request evidence.

Recovery is complete only when the endpoint is ready, error/queue metrics have
returned to the accepted range, and desired/actual GPU capacity is within the
original budget.

## Verification

Required:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/scaling-study.json >/dev/null
```

Verify SLO properties:

```bash
python3 - <<'PY'
import json
from pathlib import Path

study = json.loads(Path("artifacts/scaling-study.json").read_text())
slo = study["configuration"]["slo"]
rows = {r["strategy"]: r for r in study["results"]}
queue = rows["queue"]
assert queue["rejected"] <= slo["maximum_rejected_requests"]
assert queue["p95_wait_steps"] <= slo["maximum_p95_wait_steps"]
assert queue["scale_actions"] <= slo["maximum_scale_actions"]
assert rows["static"]["rejected"] > slo["maximum_rejected_requests"]
print("PASS: queue policy clears the authored fixture gate")
PY
```

Live verification requires:

- metric values visible and fresh;
- desired replicas never above the cap;
- scale events correlate with demand;
- Pending and readiness intervals measured;
- client success/error/deadline evidence;
- graceful drain observed;
- failure recovery within declared objective;
- load stopped and capacity restored.

## Troubleshooting

If queue scaling never adds replicas, inspect whether the metric is total or
per-Pod and whether HPA/KEDA receives a valid current value. `unknown` is not
zero.

If replicas are desired but Pending, inspect scheduler events, allocatable GPU,
taints/labels/affinity, quotas, and node provisioner logs. HPA is already doing
its part.

If nodes exist but Pods remain unready, inspect image pull, model artifact
availability, storage, GPU runtime, engine logs, startup probe, and memory fit.

If Pods oscillate, lengthen scale-down stabilization, restrict removal rate,
and compare with burst/cold-start duration. Do not hide oscillation by reducing
telemetry.

If scale-up is too slow, distinguish autoscaler reaction, node provisioning,
image pull, model download, initialization, and readiness. A warm pool or
preloaded artifact can target different terms.

If requests are lost during termination, verify endpoint removal, drain
behavior, termination grace, client cancellation/retry, and upstream timeout
ordering.

If the render script rejects the Prometheus URL, it intentionally allows only a
simple private `.svc` form. Extend the validation deliberately for TLS or
service-mesh naming; do not pass a public endpoint casually.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── scaling-study.json
├── unstable-study.json
├── expected-stability-failure.txt
├── rendered/
├── scale-timeline.json
├── hpa-or-keda-status.txt
├── events.txt
├── client-results.ndjson
├── failure-timeline.md
├── cost.md
└── report.md
```

The report must state:

- demand/workload and measured saturation signal;
- Pod and node control loops;
- min/max replicas and maximum cost;
- cold-start component times;
- queue bound and rejection policy;
- scale-up/down behavior;
- metrics failure fallback;
- drain and disruption behavior;
- normal and failure SLO results;
- Spot/on-demand assumptions;
- cleanup proof.

## Exercises

1. Replace request queue with queued prompt tokens and compare decisions.
2. Add arrival-rate prediction and measure over-provisioning versus SLO.
3. Simulate a five-step node launch plus three-step model load separately.
4. Add one warm spare and calculate availability/cost.
5. Add per-tenant queues and a fair admission policy.
6. Simulate metric loss and compare fail-open, fail-closed, and fixed fallback.
7. Add scale-to-zero and explain who receives the first request during cold
   start.
8. Model a Spot interruption notice and proactive drain.
9. Compare one large replica with several small replicas under the same GPU
   budget.
10. Add a rollout surge and prove autoscaling plus rollout cannot exceed the
    node/cost ceiling.
11. Design a retry budget that avoids a retry storm.
12. Use real KEDA/HPA conditions and Kubernetes events to build the control-loop
    timeline.

## Completion gate

You are done when:

- normal and unstable simulations behave as intended;
- you can explain why CPU misses the fixture demand;
- queue scaling satisfies the fixture SLO and improves static capacity;
- an unsafe HPA is rejected;
- rendered manifests are digest-pinned, bounded, private, and stabilized;
- you can trace desired Pod to ready GPU capacity;
- the failure drill has client, controller, Pod, node, and cost evidence;
- overload produces bounded behavior rather than an invisible unbounded queue;
- optional GPU capacity is restored exactly.

## Cleanup

Local:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

Live, stop the load source before changing capacity:

```bash
kubectl delete hpa oms-model -n "$LAB_NAMESPACE" --ignore-not-found
kubectl delete scaledobject.keda.sh oms-model \
  -n "$LAB_NAMESPACE" --ignore-not-found
kubectl delete -f artifacts/rendered/workload.yaml --ignore-not-found
kubectl get all,pvc,hpa -n "$LAB_NAMESPACE"
```

Then restore the node group to the exact saved starting configuration and verify
it. Check for load balancers, persistent volumes/snapshots, telemetry storage,
and Pending nodes. Do not assume namespace deletion completes cloud cleanup.

## Primary references

Sources were reviewed on 2026-10-21:

- [Kubernetes Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes configurable HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior)
- [Kubernetes Pod lifecycle and termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes PodDisruptionBudget](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [KEDA ScaledObject specification](https://keda.sh/docs/2.18/reference/scaledobject-spec/)
- [KEDA Prometheus scaler](https://keda.sh/docs/2.18/scalers/prometheus/)
- [AWS EKS best practices: application autoscaling](https://docs.aws.amazon.com/eks/latest/best-practices/application.html)

The simulation and static rendering paths are author-validated. No live KEDA,
custom metrics adapter, EKS node provisioner, GPU scaling, Spot interruption, or
request-drain claim was validated in this draft.
