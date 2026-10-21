# 07 — Resources and GPU scheduling

**Status:** draft
**Estimated time:** 7–10 hours across two tracks
**Compute profile:** local CPU cluster for the core lab; one EKS NVIDIA GPU node
for the optional hardware track
**Estimated GPU-minutes:** 10–45, depending on node startup time
**Prerequisites:** lessons 05 and 06; `kubectl`; `kind` for the recommended local
track; AWS CLI and authorized EKS access for the GPU track
**Static review:** 2026-10-21; shell and YAML syntax checked; live kind and EKS
GPU runtime passes are still required

## Why this matters

A Pod can be perfectly valid and remain `Pending` forever. The scheduler is not
trying to find “a powerful node.” It is finding a node that satisfies every
hard constraint at the same time:

- sufficient unreserved CPU, memory, ephemeral storage, and extended resources;
- tolerated taints;
- required labels and node affinity;
- storage and topology constraints;
- policy and plugin decisions; and
- for a GPU Pod, an integer GPU resource advertised by a device plugin.

GPU failures are especially confusing because several layers must agree:

```text
GPU hardware
  -> host driver and container runtime integration
  -> Kubernetes device plugin
  -> Node status advertises nvidia.com/gpu
  -> Pod requests nvidia.com/gpu
  -> scheduler chooses a fitting Node
  -> kubelet/device plugin allocate a device
  -> container can use the injected device and driver libraries
```

A label named `gpu=true` does not allocate a GPU. A toleration does not attract a
Pod to a GPU node. Node affinity does not reserve GPU capacity. A
`nvidia.com/gpu` request is the resource contract; labels, taints, affinity, and
topology express placement policy around it.

This lesson first makes scheduler decisions visible on a free local cluster.
Only after you can explain each decision do you repeat the process on a real EKS
GPU node.

## What you will build

### Track A — local scheduler laboratory

A three-node kind cluster:

```text
control-plane (normally tainted)

worker                         worker2
ordinary capacity              "simulated GPU" label
                               nvidia.com/gpu=true:NoSchedule taint

ordinary-workload -----------> worker
simulated-gpu-workload ------> worker2
                               ^ requires label + tolerates taint
```

You will deliberately produce three different `Pending` reasons and distribute
four replicas across worker hostnames.

### Track B — real GPU on EKS

```text
EKS API
  |
  +-- ordinary CPU nodes
  |
  \-- accelerated node
        host NVIDIA driver + container runtime
        NVIDIA device plugin -> allocatable nvidia.com/gpu: 1
                                  |
                                  v
                       nvidia-smi Pod requests exactly 1
```

You will verify advertisement, placement, allocation, and `nvidia-smi`, then
scale the managed GPU node group back to zero.

## Files in this lesson

```text
07-resources-gpu-scheduling/
├── README.md
├── local/
│   └── kind-config.yaml
├── manifests/
│   ├── 00-namespace.yaml
│   ├── 01-resource-demo.yaml
│   ├── 02-simulated-gpu-workload.yaml
│   ├── 03-ordinary-workload.yaml
│   └── 04-topology-spread.yaml
├── failures/
│   ├── 01-missing-toleration.yaml
│   ├── 02-impossible-cpu.yaml
│   └── 03-unadvertised-device.yaml
├── exercises/
│   └── SOLUTIONS.md
├── eks/
│   ├── nvidia-device-plugin-daemonset.yaml
│   ├── gpu-smoke-test.yaml
│   └── gpu-two-request-failure.yaml
└── scripts/
    ├── cleanup-local.sh
    ├── prepare-simulated-node.sh
    ├── verify-gpu.sh
    └── verify-local.sh
```

Run commands from this directory:

```bash
cd lessons/phase-01-kubernetes/07-resources-gpu-scheduling
```

## Learning outcomes

By the end, you can:

- translate CPU millicores and binary memory units;
- explain how requests affect scheduling and how limits affect execution;
- explain why scheduler decisions use declared requests rather than live usage;
- inspect Node capacity, allocatable resources, and currently allocated
  requests;
- distinguish labels, node selectors, node affinity, taints, and tolerations;
- explain required versus preferred affinity;
- use topology spread constraints without assuming they create capacity;
- describe the NVIDIA device-plugin registration and allocation path;
- prove whether `nvidia.com/gpu` is advertised and allocated;
- write a one-GPU Pod with equal integer GPU request and limit;
- prevent ordinary workloads from consuming expensive GPU nodes;
- diagnose at least five common `Pending` causes from scheduler events;
- explain why two one-GPU nodes cannot satisfy one Pod requesting two GPUs; and
- cleanly remove lab policies and return a GPU node group to zero.

## Cost and safety

Complete Track A before starting an accelerated EC2 instance.

For Track B, record these values before scaling up:

```text
cluster:
AWS Region:
managed node group:
instance type:
On-Demand or Spot:
maximum desired nodes: 1
planned maximum runtime:
cleanup owner:
```

Pricing changes by Region and time. Obtain current pricing from the official AWS
pricing pages or your organization's cost tooling. Keep the node group desired
size at zero except during a bounded lab.

The example uses a Kubernetes `Pod`, not a LoadBalancer. It creates no public
endpoint. Use On-Demand while learning so a Spot interruption is not confused
with a scheduler, driver, or application failure.

The local script refuses to label a control-plane Node. You must still inspect
the active context and pass an exact disposable worker name.

## Under the hood

### Requests are the scheduler's accounting unit

For ordinary resources:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
```

- `100m` CPU means 100 millicores, or 0.1 logical CPU.
- `64Mi` means 64 × 2²⁰ bytes.
- the scheduler adds Pod requests already assigned to a Node;
- it checks whether the new Pod's requests fit within **allocatable** capacity;
- it does not schedule from current CPU utilization shown by metrics; and
- it does not rely on the container usually using less than requested.

Simplified CPU fit:

```text
new Pod request <= Node allocatable - sum(existing scheduled Pod requests)
```

Requests reserve scheduling capacity, not a private physical slice. A CPU limit
is commonly enforced by throttling. Memory cannot be throttled the same way; a
container that exceeds an enforced memory limit can be terminated for
out-of-memory use.

Requests equal to limits for every container can contribute to `Guaranteed`
quality of service. The resource demo uses different request and limit values,
so it is `Burstable`:

```bash
kubectl get pod resource-demo -n gpu-scheduling \
  -o jsonpath='{.status.qosClass}{"\n"}'
```

### Capacity is not allocatable

```text
capacity
  - resources reserved for the operating system
  - resources reserved for Kubernetes components
  - eviction headroom and implementation reservations
  = allocatable to Pods
```

Inspect both:

```bash
kubectl get nodes \
  -o custom-columns='NAME:.metadata.name,CPU:.status.capacity.cpu,ALLOC_CPU:.status.allocatable.cpu,MEMORY:.status.capacity.memory,ALLOC_MEMORY:.status.allocatable.memory'
```

`kubectl describe node` also includes an “Allocated resources” summary. Those
percentages come from requests and limits, not live consumption.

### GPU is an extended resource

The classic NVIDIA device-plugin path works like this:

```text
NVIDIA device plugin Pod on each GPU Node
  |
  | registers with kubelet through device-plugin API
  | reports healthy device IDs
  v
kubelet publishes Node capacity/allocatable:
  nvidia.com/gpu: N
  |
  v
scheduler treats it as integer, non-overcommitted capacity
  |
  v
kubelet calls plugin Allocate for selected device IDs
  |
  v
container runtime receives device/library/runtime configuration
```

Kubernetes extended resource names contain a domain, such as
`nvidia.com/gpu`. They are integer resources. A Pod cannot request `0.5` of the
standard resource. Technologies such as NVIDIA MIG or time-slicing expose
different sharing contracts and belong in later lessons; do not assume
fractional sharing from this basic resource name.

Kubernetes permits a GPU resource in `limits`; if a request is omitted, it uses
the same value. This course writes equal request and limit explicitly because it
makes scheduling intent easy to inspect:

```yaml
requests:
  nvidia.com/gpu: 1
limits:
  nvidia.com/gpu: 1
```

### Scheduling: filter, score, bind

A useful simplified model:

```text
all Nodes
  |
  | filter hard constraints
  | - enough requested resources?
  | - required affinity/selector matches?
  | - every NoSchedule taint tolerated?
  | - required topology/storage rules satisfiable?
  v
feasible Nodes
  |
  | score soft preferences and plugin priorities
  v
chosen Node
  |
  | bind Pod .spec.nodeName
  v
kubelet starts it
```

If the feasible set is empty, the Pod remains unbound and `Pending`.

### Placement controls are not interchangeable

| Mechanism | Lives on | Meaning |
|---|---|---|
| label | Node or other object | descriptive key/value data |
| `nodeSelector` | Pod | require exact Node labels |
| required node affinity | Pod | expressive hard Node-label rule |
| preferred node affinity | Pod | scoring preference, not guarantee |
| taint | Node | repel Pods that do not tolerate it |
| toleration | Pod | permit a matching taint, not attract the Pod |
| topology spread | Pod | distribute matching Pods across topology domains |

To dedicate a GPU Node, use both sides:

```text
allocate a device and require a GPU-capable Node:
  nvidia.com/gpu request

narrow placement to one trusted GPU pool when necessary:
  required Node affinity

repel ordinary workloads:
  GPU Node NoSchedule taint

permit intended GPU workloads:
  matching toleration
```

A toleration alone allows the Pod onto the expensive Node but also allows any
other eligible Node. Affinity alone can target a GPU-labeled Node but does not
prove a free GPU exists. The extended resource request is the allocation
contract; affinity is additional pool policy.

The external teaching images retain readable version tags and pin immutable
multi-platform manifest digests. The `pause:3.10.2`,
`nvidia/cuda:12.4.1-base-ubuntu22.04`, and device-plugin `v0.19.3` digests were
resolved from their registries on 2026-10-21. Re-resolve and review platform
manifests before an intentional upgrade.

### Taint effects

- `NoSchedule`: new Pods without a matching toleration are not scheduled there.
- `PreferNoSchedule`: scheduler tries to avoid the Node but may use it.
- `NoExecute`: also evicts existing Pods without a matching toleration, subject
  to toleration timing.

This lesson uses `NoSchedule`. Adding it does not evict an ordinary Pod already
running on that Node.

### Topology spread

A topology key groups Nodes into domains. With
`topologyKey: kubernetes.io/hostname`, each Node is a domain. `maxSkew: 1` asks
for counts of matching Pods across eligible domains to differ by at most one.

- `DoNotSchedule` makes the constraint hard.
- `ScheduleAnyway` keeps it a preference when perfect spread is impossible.

Spread rules distribute Pods across existing eligible capacity. They do not
create Nodes and do not make an ineligible GPU Node eligible.

## Predict before running

Write answers:

1. A Node has 4 CPU cores and current utilization is 2%. Existing Pod requests
   total 3.8 cores. Can a new Pod requesting 500m schedule there?
2. Does a Pod with a GPU-node toleration necessarily land on a GPU Node?
3. Does a Pod with GPU-node affinity necessarily receive a GPU device?
4. What happens if a Pod requests `example.com/fake-gpu: 1` and no plugin
   advertises it?
5. Can one Pod requesting two GPUs use one GPU from each of two Nodes?
6. Does adding a `NoSchedule` taint evict an ordinary Pod already running?
7. If a device plugin is down after Node registration, which evidence would you
   inspect before blaming your model image?

## Prerequisites and preflight

### Track A preflight

The recommended path creates an isolated kind cluster with two workers:

```bash
kind create cluster --config local/kind-config.yaml
kubectl config use-context kind-llm-scheduler-lab
kubectl wait --for=condition=Ready node --all --timeout=180s
kubectl get nodes
```

Expected:

```text
llm-scheduler-lab-control-plane   Ready   control-plane
llm-scheduler-lab-worker          Ready   <none>
llm-scheduler-lab-worker2         Ready   <none>
```

If you use an existing local cluster, it needs two schedulable worker Nodes for
all placement experiments. Never repurpose a shared cluster worker.

Choose one exact worker:

```bash
kubectl get nodes \
  -l '!node-role.kubernetes.io/control-plane'
export SIM_GPU_NODE=llm-scheduler-lab-worker2
kubectl get node "$SIM_GPU_NODE"
```

The explicit `kubectl get` is a safety check before mutation.

The local mutation and cleanup scripts accept only
`kind-llm-scheduler-lab` by default. If you intentionally use a different
disposable cluster, inspect its context now. Step 2 and Cleanup show how to
prefix only the relevant command with the explicit opt-in.

```bash
kubectl config current-context
```

Do not set that override merely to bypass an unexpected context error.

### Track B preflight

Do not run these commands until you intend to start billable capacity:

```bash
aws sts get-caller-identity
aws configure get region
kubectl config current-context
kubectl auth can-i get nodes
kubectl auth can-i create pods --namespace gpu-scheduling
kubectl auth can-i create daemonsets.apps --namespace kube-system
```

The DaemonSet permission is needed only if you must install the lesson's device
plugin. A `no` answer means a cluster owner must manage that prerequisite; it
does not justify broadening your own role.

Set safe placeholders locally:

```bash
export EKS_CLUSTER='REPLACE_WITH_CLUSTER_NAME'
export GPU_NODEGROUP='REPLACE_WITH_GPU_NODE_GROUP'
export AWS_REGION='REPLACE_WITH_REGION'
```

Never commit real account, cluster, role, node-group, subnet, or registry
identifiers into this public repository.

Inspect, do not mutate:

```bash
aws eks describe-nodegroup \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,instanceTypes:instanceTypes,scaling:scalingConfig,amiType:amiType}' \
  --output yaml
```

Confirm it is the intended accelerated managed node group.

## Step-by-step lab

## Track A — free local scheduling experiments

### Step 1 — inspect Node state before changing it

```bash
kubectl get nodes --show-labels
kubectl describe node "$SIM_GPU_NODE"
```

Find:

- `Capacity` and `Allocatable`;
- `Taints`;
- labels such as `kubernetes.io/hostname`; and
- the `Allocated resources` summary.

Create the namespace and resource demo:

```bash
kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/01-resource-demo.yaml
kubectl wait --for=condition=Ready pod/resource-demo \
  -n gpu-scheduling --timeout=120s
kubectl describe pod resource-demo -n gpu-scheduling
```

Inspect declared accounting:

```bash
kubectl get pod resource-demo -n gpu-scheduling \
  -o jsonpath='request cpu={.spec.containers[0].resources.requests.cpu}{"\n"}limit cpu={.spec.containers[0].resources.limits.cpu}{"\n"}request memory={.spec.containers[0].resources.requests.memory}{"\n"}limit memory={.spec.containers[0].resources.limits.memory}{"\n"}QoS={.status.qosClass}{"\n"}'
```

Metrics, if a metrics server happens to be installed:

```bash
kubectl top pod resource-demo -n gpu-scheduling
```

`kubectl top` is optional and reports usage. It does not replace the requests
shown in the Pod spec for scheduling decisions.

### Step 2 — turn one worker into a simulated accelerator pool

```bash
./scripts/prepare-simulated-node.sh "$SIM_GPU_NODE"
```

On another intentionally selected disposable context, use:

```bash
ALLOW_NON_LAB_CONTEXT=1 \
  ./scripts/prepare-simulated-node.sh "$SIM_GPU_NODE"
```

The script applies:

```text
label: lesson.open-model-systems/accelerator=simulated-gpu
taint: nvidia.com/gpu=true:NoSchedule
```

Verify with direct API fields:

```bash
kubectl get node "$SIM_GPU_NODE" \
  -o jsonpath='{.metadata.labels.lesson\.open-model-systems/accelerator}{"\n"}{.spec.taints}{"\n"}'
```

This is only a scheduler simulation. It does **not** make a GPU resource appear
and does not install hardware.

### Step 3 — schedule intended and ordinary workloads

```bash
kubectl apply -f manifests/02-simulated-gpu-workload.yaml
kubectl apply -f manifests/03-ordinary-workload.yaml
kubectl wait --for=condition=Ready pod/simulated-gpu-workload \
  -n gpu-scheduling --timeout=120s
kubectl wait --for=condition=Ready pod/ordinary-workload \
  -n gpu-scheduling --timeout=120s
kubectl get pods -n gpu-scheduling -o wide
```

Expected:

```text
simulated-gpu-workload   Running   ...   <SIM_GPU_NODE>
ordinary-workload        Running   ...   <other worker>
```

Explain every constraint:

- simulated workload's required affinity attracts it to the labeled Node;
- its matching toleration permits the Node's taint;
- its ordinary CPU/memory requests fit;
- ordinary workload has no affinity but cannot tolerate the simulated GPU Node;
  and
- the other worker remains feasible.

Run the local check:

```bash
./scripts/verify-local.sh "$SIM_GPU_NODE"
```

### Step 4 — inspect the scheduler's output

The binding is visible as `.spec.nodeName`:

```bash
kubectl get pod simulated-gpu-workload -n gpu-scheduling \
  -o jsonpath='{.spec.nodeName}{"\n"}'
```

Events show the scheduler:

```bash
kubectl events -n gpu-scheduling \
  --for pod/simulated-gpu-workload
kubectl get events -n gpu-scheduling \
  --sort-by='.metadata.creationTimestamp'
```

`Scheduled` typically names the default scheduler and selected Node.

### Step 5 — spread replicas across Nodes

The spread demo includes the simulated GPU taint's toleration solely so both
workers are eligible for this experiment:

```bash
kubectl apply -f manifests/04-topology-spread.yaml
kubectl rollout status deployment/spread-demo \
  -n gpu-scheduling --timeout=120s
kubectl get pods -n gpu-scheduling \
  -l app.kubernetes.io/name=spread-demo \
  -o custom-columns='POD:.metadata.name,NODE:.spec.nodeName'
```

With two eligible workers and four replicas, the expected distribution is close
to 2/2. Count it:

```bash
kubectl get pods -n gpu-scheduling \
  -l app.kubernetes.io/name=spread-demo \
  -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' |
  sort | uniq -c
```

The toleration is not a pattern for ordinary production workloads. It exists to
make both lab topology domains eligible.

## Deliberate failure

### Failure 1 — required Node, missing toleration

```bash
kubectl apply -f failures/01-missing-toleration.yaml
kubectl get pod failure-missing-toleration -n gpu-scheduling
kubectl describe pod failure-missing-toleration -n gpu-scheduling
```

Expected status: `Pending`. Events should say that the labeled target Node has
an untolerated `nvidia.com/gpu` taint. Other Nodes do not match affinity.

Diagnose from constraints, then compare the working manifest:

```bash
diff -u failures/01-missing-toleration.yaml \
  manifests/02-simulated-gpu-workload.yaml || true
```

Delete the intentional failure:

```bash
kubectl delete -f failures/01-missing-toleration.yaml
```

### Failure 2 — impossible CPU request

```bash
kubectl apply -f failures/02-impossible-cpu.yaml
kubectl describe pod failure-impossible-cpu -n gpu-scheduling
```

Expected event shape:

```text
0/N nodes are available: ... Insufficient cpu ...
```

The Pod requests 100,000 CPU cores. Low live utilization cannot make that
declaration fit.

```bash
kubectl delete -f failures/02-impossible-cpu.yaml
```

### Failure 3 — syntactically valid but unadvertised device

```bash
kubectl apply -f failures/03-unadvertised-device.yaml
kubectl describe pod failure-unadvertised-device -n gpu-scheduling
```

Expected event shape:

```text
0/N nodes are available: ... Insufficient example.com/fake-gpu ...
```

The extended-resource name is valid, but no Node reports capacity for it. This
is the local analogue of requesting `nvidia.com/gpu` before the device plugin
advertises devices. The manifest specifies only a limit; Kubernetes copies an
extended-resource limit into its request when the request is omitted, so the
scheduler still sees a request for one fake GPU.

```bash
kubectl delete -f failures/03-unadvertised-device.yaml
```

### A repeatable Pending diagnostic ladder

Start with the Pod, not with random restarts:

```bash
kubectl get pod <pod> -n gpu-scheduling -o wide
kubectl describe pod <pod> -n gpu-scheduling
kubectl events -n gpu-scheduling --for pod/<pod>
```

Then inspect candidate Nodes:

```bash
kubectl get nodes --show-labels
kubectl get nodes \
  -o custom-columns='NAME:.metadata.name,TAINTS:.spec.taints,GPU:.status.allocatable.nvidia\.com/gpu,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory'
kubectl describe node <candidate-node>
```

Classify the message:

| Event fragment | Inspect next |
|---|---|
| `Insufficient cpu` or `memory` | requests, allocatable, allocated requests, autoscaler |
| `Insufficient nvidia.com/gpu` | device plugin, node allocatable, existing GPU Pods |
| `untolerated taint` | Node taints and Pod tolerations |
| `didn't match Pod's node affinity/selector` | actual Node labels and every required term |
| `unbound immediate PersistentVolumeClaims` | storage class, PVC, volume binding |
| topology/skew constraint | eligible domains, matching Pods, `maxSkew`, hard/soft mode |

`preemption is not helpful` means evicting lower-priority Pods would not solve
the listed hard constraints, for example a missing label or unadvertised GPU.

## Track B — real `nvidia.com/gpu` on EKS

Track B assumes an existing EKS cluster and accelerated managed node group. It
does not create infrastructure.

### Step 1 — scale exactly one GPU Node up

First inspect the current scaling values and record them. Then, only on the
intended lab group:

```bash
aws eks update-nodegroup-config \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --region "$AWS_REGION" \
  --scaling-config desiredSize=1
```

This assumes the inspected configuration already has `minSize: 0` and
`maxSize` of at least 1. Do not silently rewrite organization-managed bounds;
change those through the owning infrastructure workflow if necessary. Wait for
the update and Node bootstrap without assuming a fixed duration:

```bash
kubectl get nodes --watch
```

Stop when the accelerated Node is `Ready`.

### Step 2 — verify the host and advertisement layers

Current EKS accelerated AMI behavior matters:

- EKS-optimized AL2023 NVIDIA AMIs include NVIDIA drivers and the NVIDIA
  Container Toolkit, but require you to deploy the NVIDIA device plugin;
- EKS-optimized Bottlerocket NVIDIA variants include the NVIDIA device plugin;
- custom AMIs must satisfy their own driver, toolkit, runtime, and plugin
  contract.

Inspect Node labels:

```bash
kubectl get nodes \
  -L nvidia.com/gpu.present,node.kubernetes.io/instance-type,eks.amazonaws.com/nodegroup
```

EKS-optimized AL2023 and Bottlerocket NVIDIA Nodes use
`nvidia.com/gpu.present=true`. However, the classic NVIDIA device plugin's
portable contract is the advertised `nvidia.com/gpu` resource; the plugin does
not itself guarantee that feature label on every custom Kubernetes Node. Do not
invent the label on a CPU-only Node, and do not make a portable workload depend
on it unless your platform owns that labeling contract.

Inspect advertised GPU capacity:

```bash
kubectl get nodes \
  -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,GPU_CAPACITY:.status.capacity.nvidia\.com/gpu,GPU_ALLOCATABLE:.status.allocatable.nvidia\.com/gpu'
```

If the GPU columns are empty, inspect the device-plugin layer before deploying
the workload:

```bash
kubectl get daemonsets,pods --all-namespaces |
  grep -i 'nvidia.*device' || true
```

For an EKS-optimized AL2023 accelerated Node when the plugin is not already
managed by your platform, inspect the committed teaching DaemonSet:

```bash
sed -n '1,260p' eks/nvidia-device-plugin-daemonset.yaml
kubectl apply --dry-run=server \
  -f eks/nvidia-device-plugin-daemonset.yaml
kubectl apply -f eks/nvidia-device-plugin-daemonset.yaml
kubectl rollout status daemonset/nvidia-device-plugin-daemonset \
  -n kube-system --timeout=180s
```

The file is derived from NVIDIA device plugin `v0.19.3`, pins its `nvcr.io`
multi-platform image digest, and adds required affinity for the
`nvidia.com/gpu.present=true` label supplied by EKS accelerated AMIs. That
label is appropriate for placing the plugin before a GPU resource exists; the
later application Pod uses the advertised resource itself. Version `0.19.3`
and the digest were reviewed on 2026-10-21. Review upstream release notes,
rendered differences, and the new registry digest before deliberately
upgrading them.

If your organization already manages the plugin, do not install a duplicate.
Inspect its namespace, release, and version instead.

Re-check Node allocatable. The lesson cannot continue until a Node reports a
positive integer:

```bash
kubectl get nodes \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}'
```

EKS supports NVIDIA Dynamic Resource Allocation (DRA) on supported
configurations. Current EKS guidance recommends DRA for new deployments on
Kubernetes 1.34 and later when using supported static capacity, while the
traditional device plugin remains supported and is the path taught here
because it directly exposes `nvidia.com/gpu`. Do not run the DRA driver and
device plugin against the same physical GPUs: that can silently
double-advertise capacity. DRA is an optional advanced branch, not a
prerequisite for this lesson.

### Step 3 — isolate the one lab GPU Node

Choose the exact Node from its managed node-group label:

```bash
kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP" \
  -o wide
export GPU_NODE='REPLACE_WITH_EXACT_NODE_NAME'
kubectl get node "$GPU_NODE"
```

Apply a temporary lab taint:

```bash
kubectl taint node "$GPU_NODE" \
  nvidia.com/gpu=true:NoSchedule --overwrite
```

The GPU manifest contains the matching toleration. In a real managed design,
configure labels and taints in the managed node group or provisioning policy so
replacement Nodes receive them consistently; an ad-hoc Node mutation is only
for this bounded lab.

The base smoke manifest has no Node-label requirement. Its
`nvidia.com/gpu: 1` request is the hard filter and allocation contract. The
toleration merely permits the temporary taint; it does not attract the Pod to
this exact Node.

Before applying the base manifest, confirm that the intended lab Node is the
only GPU Node with free capacity. In a shared cluster with several GPU pools,
make a temporary copy and add required affinity for the EKS-managed node-group
label under `spec`:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/nodegroup
              operator: In
              values:
                - REPLACE_WITH_GPU_NODE_GROUP
```

Use the exact value already verified through
`eks.amazonaws.com/nodegroup=$GPU_NODEGROUP`; do not select a pool from an
untrusted ad-hoc label.

### Step 4 — run one real GPU Pod

Create the namespace if Track A used another cluster:

```bash
kubectl apply -f manifests/00-namespace.yaml
```

Inspect the GPU contract:

```bash
sed -n '1,240p' eks/gpu-smoke-test.yaml
```

It requires:

- a matching GPU-node toleration; and
- exactly one `nvidia.com/gpu` request and limit.

Apply:

```bash
kubectl apply -f eks/gpu-smoke-test.yaml
kubectl get pod nvidia-smi -n gpu-scheduling --watch
```

The Pod should progress `Pending` → `Running` → `Completed`. Then:

```bash
kubectl get pod nvidia-smi -n gpu-scheduling -o wide
kubectl logs nvidia-smi -n gpu-scheduling
kubectl describe pod nvidia-smi -n gpu-scheduling
```

Expected log shape:

```text
NVIDIA <model>, <memory> MiB, <driver version>
```

The exact model, memory, and driver depend on your Node. The committed command
deliberately omits the GPU UUID so ordinary lab output is safer to share.

Verify programmatically:

```bash
./scripts/verify-gpu.sh "$GPU_NODE"
```

This proves:

- the Pod completed;
- request and limit both equal 1;
- it ran on the exact Node you reviewed;
- its selected Node advertises a positive GPU count; and
- `nvidia-smi` returned data.

### Step 5 — inspect allocation accounting

```bash
kubectl describe node "$GPU_NODE"
```

In `Allocated resources`, find `nvidia.com/gpu`. A completed Pod may retain its
resource claim until the Pod object is deleted, even though its process exited.
Delete it before expecting the GPU to schedule another Pod:

```bash
kubectl delete pod nvidia-smi -n gpu-scheduling
```

### Failure 4 — one Pod cannot combine devices across Nodes

Run this only if every lab GPU Node advertises one GPU:

```bash
kubectl apply -f eks/gpu-two-request-failure.yaml
kubectl describe pod failure-needs-two-gpus-on-one-node \
  -n gpu-scheduling
```

Expected: `Pending` with `Insufficient nvidia.com/gpu`.

Even two one-GPU Nodes provide two GPUs cluster-wide, but a single Pod is
scheduled to exactly one Node. Its resource requests must fit that one Node.
Multi-node inference uses multiple Pods/processes plus distributed
communication; it does not give one Pod devices from remote Nodes.

Delete:

```bash
kubectl delete -f eks/gpu-two-request-failure.yaml
```

## Troubleshooting

### GPU field is absent from Node allocatable

Inspect in this order:

1. Is this actually a GPU EC2 instance?
2. Did the correct accelerated AMI/custom image boot?
3. Is the host driver healthy?
4. Is the NVIDIA container runtime/toolkit configured?
5. Is exactly one intended device-plugin DaemonSet running on the Node?
6. What do device-plugin Pod logs say?
7. Did kubelet update Node capacity after plugin registration?

Commands:

```bash
kubectl get node "$GPU_NODE" -o yaml
kubectl get pods --all-namespaces -o wide |
  grep "$GPU_NODE"
kubectl logs -n kube-system \
  daemonset/nvidia-device-plugin-daemonset --all-pods=true --prefix
```

Adjust namespace and DaemonSet name to your managed installation.

### GPU advertised, but Pod is Pending

```bash
kubectl describe pod nvidia-smi -n gpu-scheduling
kubectl get node "$GPU_NODE" \
  -o jsonpath='{.metadata.labels}{"\n"}{.spec.taints}{"\n"}{.status.allocatable}{"\n"}'
kubectl get pods --all-namespaces \
  -o custom-columns='NS:.metadata.namespace,POD:.metadata.name,NODE:.spec.nodeName,GPU:.spec.containers[*].resources.limits.nvidia\.com/gpu'
```

Check resource availability, label/affinity match, taints/tolerations, namespace
quota, and existing completed Pods that have not been deleted.

### Pod starts but `nvidia-smi` is missing or fails

This is no longer a scheduler-only problem. Inspect:

- exact image and command;
- Node AMI and driver;
- container runtime integration;
- device-plugin logs and allocation response; and
- devices visible in the container.

Do not “solve” compatibility by randomly changing CUDA images. Record host
driver, GPU model, image, CUDA user-space version, and error together.

### Ordinary Pod still runs on a Node you just tainted

`NoSchedule` blocks new scheduling; it does not evict an existing Pod. Delete or
move the workload through its controller only after checking ownership. Use
`NoExecute` only when you understand eviction consequences.

### Autoscaler does not create a fitting Node

Scheduler events describe the unsatisfied Pod; autoscaler/provisioner logs
describe why capacity was not created. Check instance-type constraints, quotas,
subnet/AZ capacity, maximum node-group size, labels/taints on generated Nodes,
and daemon overhead.

## Lab outline

1. Inspect Node capacity, allocatable resources, and allocated requests.
2. Declare CPU/memory requests and limits.
3. Label and taint one disposable worker as a simulated accelerator.
4. Schedule an intended workload using affinity plus toleration.
5. prove an ordinary Pod is repelled;
6. spread replicas across hostname topology;
7. diagnose missing toleration, impossible CPU, and unadvertised-resource
   failures;
8. on EKS, scale one accelerated Node up;
9. verify driver/runtime/plugin advertisement;
10. isolate it with a temporary taint;
11. schedule exactly one `nvidia.com/gpu` Pod and run `nvidia-smi`;
12. prove one Pod cannot aggregate GPUs across Nodes; and
13. delete workloads and return desired GPU capacity to zero.

## Evidence to collect

For Track A:

```bash
mkdir -p evidence/lesson-07
kubectl get nodes --show-labels > evidence/lesson-07/local-nodes.txt
kubectl get pods -n gpu-scheduling -o wide \
  > evidence/lesson-07/local-placement.txt
kubectl get events -n gpu-scheduling \
  --sort-by='.metadata.creationTimestamp' \
  > evidence/lesson-07/local-events.txt
```

For Track B, review and redact before saving:

```bash
kubectl get nodes \
  -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,GPU:.status.allocatable.nvidia\\.com/gpu'
kubectl describe pod nvidia-smi -n gpu-scheduling
kubectl logs nvidia-smi -n gpu-scheduling
```

Your report must include:

- request-fit arithmetic for one scheduled and one Pending Pod;
- a table mapping each failure to the exact scheduler event;
- Node label, taint, Pod affinity, toleration, and resource interactions;
- device-plugin execution flow;
- the selected Node's allocatable GPU count;
- GPU Pod request/limit and sanitized `nvidia-smi` output; and
- proof that desired GPU node-group capacity returned to zero.

Never publish account IDs, instance IDs, private addresses, GPU UUIDs, cluster
names, IAM roles, or credentials.

## Exercises

Complete these before opening `exercises/SOLUTIONS.md`.

### Exercise 1 — calculate fit

Given a Node with 3900m allocatable CPU and 7Gi allocatable memory, existing
requests of 3200m and 5Gi, decide whether these Pods fit:

1. 500m CPU and 1Gi memory;
2. 800m CPU and 512Mi memory;
3. 100m CPU and 3Gi memory.

Show arithmetic for both resources.

### Exercise 2 — preferred versus required affinity

Make a temporary copy of the simulated workload. Replace required affinity with
preferred affinity. Remove the label from the target Node, recreate the Pod, and
explain why it can schedule elsewhere.

### Exercise 3 — taint semantics

Create an ordinary Pod before applying `NoSchedule`, then taint its Node. Prove
the Pod stays. Compare this behavior with the documented meaning of `NoExecute`.
Do not apply `NoExecute` to a shared Node.

### Exercise 4 — strict topology

Change `ScheduleAnyway` to `DoNotSchedule`, scale beyond easily balanced
capacity, and predict which replicas remain Pending when an eligible topology
domain disappears.

### Exercise 5 — write a Pending decision tree

Starting only from `kubectl get pod`, create a flowchart that separates:

- image/runtime failures;
- unsatisfied resource requests;
- affinity/selector mismatch;
- taint mismatch;
- storage binding; and
- topology constraints.

The scheduler only explains pre-binding `Pending`; distinguish it from a Pod
that was scheduled but cannot start.

### Exercise 6 — GPU placement policy review

Explain why each of these is insufficient alone:

1. `nodeSelector: gpu=true`;
2. a GPU taint on Nodes;
3. a toleration on Pods;
4. only `nvidia.com/gpu: 1`; and
5. only topology spread.

Design the minimal combined policy for a dedicated inference pool.

## Verification

Local:

```bash
kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/02-simulated-gpu-workload.yaml
kubectl apply -f manifests/03-ordinary-workload.yaml
./scripts/verify-local.sh "$SIM_GPU_NODE"
```

Real GPU:

```bash
kubectl apply -f eks/gpu-smoke-test.yaml
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded \
  pod/nvidia-smi -n gpu-scheduling --timeout=180s
./scripts/verify-gpu.sh "$GPU_NODE"
```

If the image must be pulled and initialized, increase the timeout based on
observed events rather than repeatedly deleting the Pod.

## Completion gate

You pass when:

- local verification proves intended and ordinary placement;
- you can explain all three local Pending events without guessing;
- if you took Track B, GPU verification records a successful allocation;
- you can draw the device plugin → Node allocatable → scheduler → kubelet
  allocation path;
- you can explain why labels, taints, affinity, and GPU resources are different;
- all intentional failures are deleted; and
- any GPU node group used for the lab is verified at desired size zero.

Track A is mandatory. Track B may be deferred until budget/capacity is approved;
reading it is not equivalent to completing it.

## Cleanup

### Track A

Remove lesson objects plus the temporary label and taint:

```bash
./scripts/cleanup-local.sh "$SIM_GPU_NODE"
```

The script verifies the local context, namespace labels, course marker label,
and exact taint before deleting or changing anything. If Track A used another
disposable context, opt in for this command only:

```bash
ALLOW_NON_LAB_CONTEXT=1 ./scripts/cleanup-local.sh "$SIM_GPU_NODE"
```

If the cluster exists only for this lesson:

```bash
kind delete cluster --name llm-scheduler-lab
```

### Track B

Delete workload objects first:

```bash
kubectl config current-context
kubectl get namespace gpu-scheduling --show-labels
kubectl delete namespace gpu-scheduling \
  --ignore-not-found --wait=true --timeout=180s
```

Remove the temporary taint if the Node still exists:

```bash
if kubectl get node "$GPU_NODE" >/dev/null 2>&1; then
  kubectl taint node "$GPU_NODE" nvidia.com/gpu:NoSchedule-
fi
```

Do not uninstall an organization-managed device plugin. If you applied this
lesson's DaemonSet and no other workloads need it:

```bash
kubectl delete -f eks/nvidia-device-plugin-daemonset.yaml
```

Return the intended managed group to zero:

```bash
aws eks update-nodegroup-config \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --region "$AWS_REGION" \
  --scaling-config desiredSize=0
```

Verify through AWS, not merely by watching the Pod disappear:

```bash
aws eks describe-nodegroup \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --region "$AWS_REGION" \
  --query 'nodegroup.scalingConfig' \
  --output yaml
kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP"
```

The requested desired size must be `0`. Node termination is asynchronous, so
continue observing until no unintended GPU Node remains.

Also check that the lab created no Service of type LoadBalancer and no
persistent volume:

```bash
kubectl get services --all-namespaces
kubectl get persistentvolumes
```

Interpret existing shared resources carefully; do not delete resources merely
because these inventory commands display them.

## Primary references

Kubernetes and NVIDIA upstream:

- [Resource management for Pods and containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Taints and tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Pod topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Scheduling GPUs](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Device plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/)
- [Pod quality of service classes](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)
- [NVIDIA Kubernetes device plugin](https://github.com/NVIDIA/k8s-device-plugin)
- [NVIDIA device plugin v0.19.3](https://github.com/NVIDIA/k8s-device-plugin/releases/tag/v0.19.3)
- [NVIDIA Container Toolkit architecture](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)

AWS upstream:

- [EKS-optimized accelerated AMIs](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-ami.html)
- [Accelerated AMI releases](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-versions.html)
- [NVIDIA device management on EKS](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia-dra-device-plugin.html)
- [Update managed node-group configuration](https://docs.aws.amazon.com/cli/latest/reference/eks/update-nodegroup-config.html)
- [Amazon EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)

Reference review date: 2026-10-21.
