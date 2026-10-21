# Lesson 07 exercise solutions

Attempt each exercise before reading this file. Use only disposable lab Nodes
for mutations.

## Exercise 1 — calculate fit

Available after existing requests:

```text
CPU:    3900m - 3200m = 700m
memory: 7Gi - 5Gi = 2Gi
```

Results:

1. `500m`, `1Gi` fits both resources.
2. `800m`, `512Mi` fails CPU because 800m is greater than 700m.
3. `100m`, `3Gi` fails memory because 3Gi is greater than 2Gi.

A Pod must fit every requested resource on one Node. Spare memory cannot
compensate for insufficient CPU, and spare CPU cannot compensate for memory.

## Exercise 2 — preferred versus required affinity

Copy the working file:

```bash
cp manifests/02-simulated-gpu-workload.yaml \
  /tmp/preferred-simulated-gpu.yaml
```

In the copy:

- change the Pod name;
- replace `requiredDuringSchedulingIgnoredDuringExecution` with
  `preferredDuringSchedulingIgnoredDuringExecution`;
- under it, add list item fields `weight: 100` and `preference:` before the
  existing `matchExpressions`; and
- keep the toleration.

The affinity shape is:

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: lesson.open-model-systems/accelerator
              operator: In
              values:
                - simulated-gpu
```

Remove the label, create the Pod, and inspect:

```bash
kubectl label node "$SIM_GPU_NODE" \
  lesson.open-model-systems/accelerator-
kubectl apply -f /tmp/preferred-simulated-gpu.yaml
kubectl get pod -n gpu-scheduling -o wide
kubectl describe pod -n gpu-scheduling <temporary-pod-name>
```

Preferred affinity affects scoring; it does not make the Pod unschedulable when
no Node matches. The Pod can use another feasible worker.

Delete the temporary Pod and restore the label:

```bash
kubectl delete -f /tmp/preferred-simulated-gpu.yaml
kubectl label node "$SIM_GPU_NODE" \
  lesson.open-model-systems/accelerator=simulated-gpu --overwrite
```

## Exercise 3 — taint semantics

On a fresh disposable worker, schedule an ordinary Pod first. Record its Node:

```bash
kubectl apply -f manifests/03-ordinary-workload.yaml
ORDINARY_NODE="$(kubectl get pod ordinary-workload -n gpu-scheduling \
  -o jsonpath='{.spec.nodeName}')"
printf '%s\n' "$ORDINARY_NODE"
```

Apply a `NoSchedule` taint:

```bash
kubectl taint node "$ORDINARY_NODE" \
  lesson.open-model-systems/test=true:NoSchedule --overwrite
kubectl get pod ordinary-workload -n gpu-scheduling -o wide
```

The existing Pod remains. `NoSchedule` filters new scheduling decisions. A
`NoExecute` taint additionally causes Pods without tolerations to be evicted.
Do not test `NoExecute` on a shared Node.

Clean up:

```bash
kubectl taint node "$ORDINARY_NODE" \
  lesson.open-model-systems/test-
```

## Exercise 4 — strict topology

Make a temporary copy and change:

```yaml
whenUnsatisfiable: DoNotSchedule
```

Strict behavior becomes visible when eligible topology domains and replica
counts cannot satisfy `maxSkew`. For example, first ensure replicas exist across
two workers, then make one domain ineligible for replacement Pods and delete
one Pod from the remaining domain.

Inspect:

```bash
kubectl get pods -n gpu-scheduling \
  -l app.kubernetes.io/name=spread-demo -o wide
kubectl describe pod <pending-pod> -n gpu-scheduling
```

The exact experiment depends on current Pods because existing Pods influence
skew calculations. The central result is that `DoNotSchedule` can leave a Pod
Pending, while `ScheduleAnyway` makes imbalance a scoring preference.

## Exercise 5 — Pending decision tree

One useful decision tree:

```text
Pod Pending
  |
  +-- .spec.nodeName empty?
  |     |
  |     +-- yes: scheduler has not bound it
  |           |
  |           +-- FailedScheduling events
  |                 +-- insufficient resource -> requests/allocatable/usage claims
  |                 +-- untolerated taint -> taint/toleration
  |                 +-- affinity mismatch -> real labels/required terms
  |                 +-- unbound PVC -> PVC/StorageClass/volume topology
  |                 \-- spread constraint -> domains/skew/hardness
  |
  \-- .spec.nodeName set?
        |
        +-- scheduler completed; inspect kubelet/runtime path
              +-- image pull
              +-- missing volume/config/secret
              +-- sandbox/network setup
              +-- init container
              \-- container crash
```

Commands:

```bash
kubectl get pod <pod> -n <namespace> -o wide
kubectl describe pod <pod> -n <namespace>
kubectl events -n <namespace> --for pod/<pod>
```

## Exercise 6 — GPU placement policy review

Why each alone is incomplete:

1. `nodeSelector: gpu=true` targets a label but allocates no device and the
   label can be wrong.
2. A GPU taint repels ordinary Pods but admits no intended Pod without a
   toleration.
3. A toleration permits a Node but does not require it or allocate a GPU.
4. `nvidia.com/gpu: 1` allocates a GPU and inherently limits candidates to
   Nodes advertising one, but does not by itself protect GPU Nodes from
   non-GPU Pods.
5. Topology spread distributes matching Pods across eligible domains but does
   not define accelerator capacity or isolation.

A minimal dedicated-pool policy:

```yaml
spec:
  tolerations:
    - key: nvidia.com/gpu
      operator: Equal
      value: "true"
      effect: NoSchedule
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: eks.amazonaws.com/nodegroup
                operator: In
                values: ["gpu-inference"]
  containers:
    - name: server
      resources:
        requests:
          nvidia.com/gpu: 1
        limits:
          nvidia.com/gpu: 1
```

Replace `gpu-inference` with the exact reviewed managed node-group value. The
Nodes also need the matching `NoSchedule` taint. In EKS, make the policy durable
in the managed node-group or provisioner configuration so replacement Nodes
inherit it. The `nvidia.com/gpu` request, not the node-group label, is what
allocates a device.
