# 05 — Kubernetes objects and reconciliation

**Status:** draft
**Estimated time:** 5–7 hours
**Compute profile:** local CPU Kubernetes cluster
**Estimated GPU-minutes:** 0
**Prerequisites:** lesson 04; basic shell commands; an OCI-compatible container
client; `kubectl`; `curl`
**Static review:** 2026-10-21 against the stable Kubernetes APIs used here
(`v1` and `apps/v1`); a complete kind runtime pass is still required

## Why this matters

An inference server on Kubernetes is not “a process on a remote machine.” It is
a collection of API objects. A Deployment says how many copies should exist, a
Service selects the copies that receive traffic, and controllers repeatedly try
to make reality match those declarations.

If you skip this mental model, ordinary events look mysterious:

- deleting a Pod appears not to work because another Pod immediately appears;
- changing a label makes a healthy application unreachable;
- editing a managed Pod is lost when its controller replaces it;
- `Running` is mistaken for “the application is ready and reachable”; and
- a rollout stalls because desired and observed state disagree.

This lesson builds the smallest useful web workload twice: first as a naked Pod,
then as a Deployment plus a Service. You will inspect every object in the
ownership chain, deliberately break a selector, and explain the repair from
evidence rather than guesswork.

## What you will build

```text
Laptop curl
     |
     | kubectl port-forward
     v
Service hello-systems :80
     |
     | selector matches Pod labels
     v
EndpointSlice
  |             |             |
Pod A :8080   Pod B :8080   Pod C :8080
       \          |          /
        owned by one ReplicaSet
                   |
             owned by Deployment
```

The application is Kubernetes' small `agnhost` HTTP test server. It returns the
Pod hostname, making replacement Pods and Service routing visible.

## Files in this lesson

```text
05-kubernetes-objects-reconciliation/
├── README.md
├── manifests/
│   ├── 00-namespace.yaml
│   ├── 01-standalone-pod.yaml
│   ├── 02-deployment.yaml
│   └── 03-service.yaml
├── failures/
│   └── service-selector-mismatch.yaml
├── local/
│   └── kind-config.yaml
├── exercises/
│   └── SOLUTIONS.md
└── scripts/
    ├── cleanup.sh
    ├── preflight.sh
    └── verify.sh
```

Run commands from this directory:

```bash
cd lessons/phase-01-kubernetes/05-kubernetes-objects-reconciliation
```

## Learning outcomes

By the end, you can:

- describe the API server, etcd, scheduler, controllers, kubelet, container
  runtime, and network plugin without treating Kubernetes as magic;
- read the important fields in Kubernetes YAML;
- use `kubectl apply`, `get`, `describe`, `logs`, `exec`, `wait`, and events;
- explain the difference between a Pod, ReplicaSet, Deployment, and Service;
- use labels and selectors as a join between objects;
- distinguish desired state, observed state, and reconciliation;
- follow owner references from a Pod to its ReplicaSet and Deployment;
- predict whether a deleted object will be recreated, and by which controller;
- diagnose “Pods are healthy, but the Service has no endpoints”; and
- remove every object created by the lesson.

## Cost and safety

This lesson needs no cloud resources and no GPU. Prefer `kind`, Minikube, Docker
Desktop Kubernetes, or another disposable local cluster. If you use EKS anyway,
worker nodes still cost money. Do not create a public LoadBalancer; the Service
is deliberately `ClusterIP`.

The manifests use a dedicated `llm-systems` namespace. Never run a delete command
until you have checked the active context printed by the preflight script.

## Under the hood

### Kubernetes is an API with control loops

```text
you / CI
   |
   | kubectl sends authenticated HTTPS requests
   v
+---------------- Kubernetes control plane ----------------+
| API server <----> etcd                                   |
|     ^              durable API object data               |
|     |                                                    |
|     +---- Deployment controller                          |
|     +---- ReplicaSet controller                          |
|     +---- scheduler                                      |
+----------------------------------------------------------+
             | watches and object updates
             v
+----------------------- each node ------------------------+
| kubelet ---> container runtime ---> application process  |
|       \---- network/storage/device plugins               |
+----------------------------------------------------------+
```

The components do not form one giant imperative script:

1. `kubectl apply` submits an object to the API server.
2. The API server authenticates, authorizes, validates, defaults, and persists
   it.
3. Components **watch** the API for relevant changes.
4. A controller compares desired state with observed state.
5. The controller creates or updates objects to reduce the difference.
6. The scheduler chooses a Node for each unbound Pod.
7. The kubelet on that Node asks the container runtime to start containers and
   reports status through the API.

This loop repeats. That repeated convergence is **reconciliation**.

### Desired state versus observed state

For a Deployment:

```yaml
spec:
  replicas: 3
```

is desired state. Fields such as these are observed state:

```yaml
status:
  replicas: 3
  availableReplicas: 3
```

You normally write `spec`; Kubernetes components write `status`. A healthy
system does not require the two to be identical at every instant. During a
rollout, desired state may be three replicas while only two are currently
available. Reconciliation closes that gap.

### What each object means

| Object | Job | Recreates a deleted Pod? |
|---|---|---:|
| Pod | Runs one or more tightly coupled containers | No, unless a controller owns it |
| ReplicaSet | Keeps a chosen number of matching Pods | Yes |
| Deployment | Manages ReplicaSets and rolling revisions | Indirectly |
| Service | Gives selected Pods a stable virtual address and DNS name | No |

A container restart inside an existing Pod is generally driven by the kubelet
according to the Pod's restart policy. Creating a replacement Pod after the old
Pod object disappears is a controller action. These are different mechanisms.

### Object and YAML anatomy

Every normal Kubernetes object has four top-level ideas:

```yaml
apiVersion: v1       # API group and version
kind: Pod            # object type
metadata:            # identity, namespace, labels, annotations
spec:                # desired state for this kind
```

After creation, the server adds fields such as `metadata.uid`,
`metadata.resourceVersion`, `metadata.creationTimestamp`, and `status`.

Important details in this lesson's manifests:

- `metadata.namespace` prevents accidental creation in `default`;
- labels are key/value metadata used for grouping and selection;
- `spec.containers` is a list even with one container;
- external images show a readable version tag and also pin an immutable
  multi-platform manifest digest;
- `containerPort` documents a listening port but does not expose it;
- resource requests influence scheduling while limits constrain consumption;
- a Deployment's selector must match labels in its Pod template; and
- a Service selector independently matches Pod labels.

For example, the manifests use
`registry.k8s.io/e2e-test-images/agnhost:2.53@sha256:...`. Kubernetes pulls the
digest; the tag documents the upstream release for humans. The checked-in
digest was resolved directly from `registry.k8s.io` on 2026-10-21. Re-resolve
and review the platform manifest before intentionally upgrading it.

Ask the API schema instead of memorizing fields:

```bash
kubectl explain pod
kubectl explain pod.spec
kubectl explain pod.spec.containers.resources
kubectl explain deployment.spec.strategy --recursive
```

`kubectl` parses YAML and sends an API request. Indentation is not cosmetic: it
changes the data structure.

## Predict before running

Write down your answers. Do not optimize for being correct; a wrong prediction
followed by a good explanation is useful.

1. Which component chooses a Node for a new Pod?
2. If you delete a standalone Pod, who recreates it?
3. If you delete a Deployment-owned Pod, who recreates it?
4. Does `containerPort: 8080` make an application reachable from your laptop?
5. If all Pods are healthy but a Service selector matches none, what happens?
6. Does a Service route to a Deployment or directly to selected Pod endpoints?

## Prerequisites and preflight

### Install the local tools

The primary path uses kind: Kubernetes Nodes run as containers on your laptop.
You need:

- a working Docker installation or another runtime supported by kind;
- `kind`;
- `kubectl`; and
- `curl`.

Follow the official installation pages for your operating system:

- [Install Docker Engine](https://docs.docker.com/engine/install/) or use an
  already working compatible container runtime;
- [Install kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation);
- [Install kubectl](https://kubernetes.io/docs/tasks/tools/); and
- use the `curl` package supplied by your operating system.

For example, on macOS with Homebrew:

```bash
brew install kind kubectl
```

Docker Desktop is installed separately from its official installer. On other
operating systems, use the official instructions above rather than copying a
binary for the wrong CPU architecture.

Verify the local tools before creating anything:

```bash
docker info
kind version
kubectl version --client
curl --version
```

If you use Podman or another kind-supported provider, replace the Docker
preflight with that provider's official check.

### Create the course cluster

The committed configuration creates one control-plane Node and one worker:

```bash
kind create cluster \
  --name llm-lab \
  --config local/kind-config.yaml \
  --wait 180s
```

Expected shape:

```text
Creating cluster "llm-lab" ...
...
Set kubectl context to "kind-llm-lab"
```

Creating a cluster also writes/selects a kubeconfig context. Confirm it
explicitly:

```bash
kubectl config current-context
kubectl get nodes -o wide
```

Expected context:

```text
kind-llm-lab
```

Expected Nodes:

```text
llm-lab-control-plane   Ready   control-plane
llm-lab-worker          Ready   <none>
```

Exact versions, IPs, and ages vary. If `kind create cluster` reports the cluster
already exists, inspect it rather than deleting it blindly:

```bash
kind get clusters
kubectl config get-contexts
```

Minikube and Docker Desktop Kubernetes are valid alternatives, but the commands
below are validated against kind. If you use an alternative, make sure it has a
Ready schedulable Node and keep using its exact context.

### Run lesson safety checks

You need a reachable cluster with at least one Ready node:

```bash
./scripts/preflight.sh
```

Expected shape:

```text
kubectl client: ...
current context: kind-llm-lab
node/... condition met
preflight passed
```

By default, the script accepts only the course context `kind-llm-lab`. This
prevents a copied command from silently targeting whatever cluster happened to
be current. If you intentionally use another disposable local cluster, inspect
its context first and opt in explicitly:

```bash
kubectl config current-context
ALLOW_NON_LAB_CONTEXT=1 ./scripts/preflight.sh
```

Before the namespace exists, perform a client-side structural check without
persisting anything:

```bash
kubectl apply --dry-run=client -f manifests/
```

Expected shape:

```text
namespace/llm-systems created (dry run)
pod/standalone-web created (dry run)
deployment.apps/hello-systems created (dry run)
service/hello-systems created (dry run)
```

Client dry-run is weaker than server dry-run. A namespaced server dry-run cannot
succeed before `llm-systems` really exists, so you will run the stronger check
immediately after creating the namespace in Step 1.

## Step-by-step lab

### Step 1 — create a namespace

```bash
kubectl apply -f manifests/00-namespace.yaml
kubectl get namespace llm-systems
export LESSON_NS=llm-systems
```

Now that the namespace exists, ask the API server to validate, default,
authorize, and admit the remaining objects without storing them:

```bash
kubectl apply --dry-run=server -f manifests/01-standalone-pod.yaml
kubectl apply --dry-run=server -f manifests/02-deployment.yaml
kubectl apply --dry-run=server -f manifests/03-service.yaml
```

If your account cannot use server dry-run, repeat with `--dry-run=client` and
understand that admission and server-side validation were not exercised.

Apply it again:

```bash
kubectl apply -f manifests/00-namespace.yaml
```

Expected:

```text
namespace/llm-systems unchanged
```

`apply` is declarative and idempotent: an unchanged declaration does not create
a duplicate.

### Step 2 — create a standalone Pod

Read the file:

```bash
sed -n '1,240p' manifests/01-standalone-pod.yaml
```

Apply and wait:

```bash
kubectl apply -f manifests/01-standalone-pod.yaml
kubectl wait --for=condition=Ready pod/standalone-web \
  -n "$LESSON_NS" --timeout=120s
kubectl get pod standalone-web -n "$LESSON_NS" -o wide
```

Expected shape:

```text
NAME             READY   STATUS    RESTARTS   AGE   IP          NODE
standalone-web   1/1     Running   0          ...   10.x.x.x    ...
```

`Running` is the Pod phase. `READY 1/1` says its one container is ready. Lesson
06 shows why these can differ.

### Step 3 — inspect the Pod with `kubectl`

Compact table:

```bash
kubectl get pods -n "$LESSON_NS"
```

Human-oriented detail, including recent events:

```bash
kubectl describe pod standalone-web -n "$LESSON_NS"
```

Raw API object:

```bash
kubectl get pod standalone-web -n "$LESSON_NS" -o yaml
```

Machine-selectable fields:

```bash
kubectl get pod standalone-web -n "$LESSON_NS" \
  -o jsonpath='{.metadata.uid}{"\n"}{.spec.nodeName}{"\n"}{.status.podIP}{"\n"}'
```

Application logs:

```bash
kubectl logs pod/standalone-web -n "$LESSON_NS"
```

Expected log shape:

```text
... Started HTTP server on port 8080
```

Execute a process in the running container:

```bash
kubectl exec -n "$LESSON_NS" pod/standalone-web -- /agnhost --help
```

This starts a process **inside the existing container namespaces**. It does not
SSH to the Node and it does not create another Pod.

Forward a laptop port to the Pod:

```bash
kubectl port-forward -n "$LESSON_NS" pod/standalone-web 18080:8080
```

Leave that terminal open. In a second terminal:

```bash
curl --fail --silent http://127.0.0.1:18080/hostname
```

Expected: the response contains `standalone-web`. Stop port-forward with
`Ctrl-C`.

Inspect scheduling events:

```bash
kubectl events -n "$LESSON_NS" --for pod/standalone-web
```

If an older client lacks `kubectl events`, use:

```bash
kubectl get events -n "$LESSON_NS" \
  --field-selector involvedObject.name=standalone-web \
  --sort-by='.metadata.creationTimestamp'
```

Look for this shape:

```text
Scheduled -> Pulling/Pulled -> Created -> Started
```

Events are bounded, short-lived diagnostics, not a permanent audit log.

### Step 4 — prove a standalone Pod has no replacement controller

```bash
kubectl delete pod standalone-web -n "$LESSON_NS"
kubectl get pods -n "$LESSON_NS"
```

Expected: no Pod named `standalone-web` returns. No controller owns this Pod, so
none restores it.

### Step 5 — create a Deployment

```bash
kubectl apply -f manifests/02-deployment.yaml
kubectl rollout status deployment/hello-systems \
  -n "$LESSON_NS" --timeout=120s
kubectl get deployments,replicasets,pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems
```

Expected shape:

```text
NAME                            READY   UP-TO-DATE   AVAILABLE
deployment.apps/hello-systems   3/3     3            3

NAME                                  DESIRED   CURRENT   READY
replicaset.apps/hello-systems-<hash>   3         3         3

NAME                                READY   STATUS
pod/hello-systems-<hash>-<suffix>   1/1     Running
... three Pods total ...
```

Generated suffixes are expected. Never automate against their exact values.

### Step 6 — follow the ownership chain

Choose a Pod:

```bash
POD_NAME="$(kubectl get pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems \
  -o jsonpath='{.items[0].metadata.name}')"
printf '%s\n' "$POD_NAME"
```

Read its owner:

```bash
kubectl get pod "$POD_NAME" -n "$LESSON_NS" \
  -o jsonpath='{range .metadata.ownerReferences[*]}{.kind}{"/"}{.name}{"\n"}{end}'
```

Expected:

```text
ReplicaSet/hello-systems-<hash>
```

Then inspect that ReplicaSet's owner:

```bash
RS_NAME="$(kubectl get pod "$POD_NAME" -n "$LESSON_NS" \
  -o jsonpath='{.metadata.ownerReferences[0].name}')"
kubectl get replicaset "$RS_NAME" -n "$LESSON_NS" \
  -o jsonpath='{range .metadata.ownerReferences[*]}{.kind}{"/"}{.name}{"\n"}{end}'
```

Expected:

```text
Deployment/hello-systems
```

The actual graph is:

```text
Deployment hello-systems
  owns -> ReplicaSet hello-systems-<pod-template-hash>
             owns -> Pod A
             owns -> Pod B
             owns -> Pod C
```

The Deployment controller manages revisions as ReplicaSets. The ReplicaSet
controller manages the replica count. Neither runs the container; the kubelet
on the selected Node does.

### Step 7 — watch reconciliation replace a Pod

Record identities:

```bash
kubectl get pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,NODE:.spec.nodeName'
```

Delete the chosen Pod and immediately watch:

```bash
kubectl delete pod "$POD_NAME" -n "$LESSON_NS"
kubectl get pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems --watch
```

Stop with `Ctrl-C` after a replacement is `Running`.

What happened:

1. desired replicas remained 3;
2. observed matching Pods fell to 2;
3. the ReplicaSet controller created a new Pod;
4. the scheduler selected a Node; and
5. that Node's kubelet started the container.

The replacement has a new name and UID. Kubernetes repaired the count; it did
not resurrect the deleted object.

### Step 8 — scale desired state

```bash
kubectl scale deployment/hello-systems -n "$LESSON_NS" --replicas=5
kubectl rollout status deployment/hello-systems \
  -n "$LESSON_NS" --timeout=120s
kubectl get deployment hello-systems -n "$LESSON_NS"
```

This imperative command updates the API field `spec.replicas`, but the
checked-in file still says 3. Re-apply it:

```bash
kubectl apply -f manifests/02-deployment.yaml
kubectl rollout status deployment/hello-systems \
  -n "$LESSON_NS" --timeout=120s
kubectl get pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems
```

Expected: three Pods. This is why Git-managed declarations and undocumented
production changes can fight each other.

### Step 9 — create a Service

A Pod IP is ephemeral. A Service supplies a stable name and virtual IP for a
changing set of Pods.

```bash
kubectl apply -f manifests/03-service.yaml
kubectl get service hello-systems -n "$LESSON_NS"
kubectl get endpointslice -n "$LESSON_NS" \
  -l kubernetes.io/service-name=hello-systems
```

Expected Service shape:

```text
NAME            TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)
hello-systems   ClusterIP   10.x.x.x     <none>        80/TCP
```

The EndpointSlice should contain three ready endpoint addresses.

### Step 10 — prove selectors are the connection

Show labels:

```bash
kubectl get pods -n "$LESSON_NS" --show-labels
```

Run the same query as the Service:

```bash
kubectl get pods -n "$LESSON_NS" \
  -l 'app.kubernetes.io/name=hello-systems,app.kubernetes.io/component=web'
```

Read the selector:

```bash
kubectl get service hello-systems -n "$LESSON_NS" \
  -o jsonpath='{.spec.selector}{"\n"}'
```

Kubernetes does not connect this Service to the Deployment by matching object
names. The join is:

```text
Service .spec.selector
        |
        | matches labels
        v
Pod .metadata.labels
```

The control plane builds EndpointSlices from the match. Cluster networking then
uses those ready endpoints.

### Step 11 — call the Service safely

```bash
kubectl port-forward -n "$LESSON_NS" service/hello-systems 18080:80
```

In another terminal:

```bash
for i in 1 2 3 4 5; do
  curl --fail --silent http://127.0.0.1:18080/hostname
  printf '\n'
done
```

You may see different Pod hostnames. Repetition does not guarantee every replica
appears; exact balancing order is not this lesson's contract. Stop with
`Ctrl-C`.

## Deliberate failure — healthy Pods, empty Service

Before applying the failure, predict:

1. Will the Deployment become unhealthy?
2. Will Pod logs show an application crash?
3. What will happen to the EndpointSlice?
4. What will traffic through the Service report?

Break only the Service selector:

```bash
kubectl apply -f failures/service-selector-mismatch.yaml
kubectl get pods -n "$LESSON_NS" \
  -l app.kubernetes.io/name=hello-systems
kubectl get endpointslice -n "$LESSON_NS" \
  -l kubernetes.io/service-name=hello-systems
```

The Pods remain ready. The Service now selects
`app.kubernetes.io/name=hello-systemz`, which no Pod has. Its EndpointSlice has
no usable addresses.

Confirm the mismatch from both sides:

```bash
kubectl get service hello-systems -n "$LESSON_NS" \
  -o jsonpath='{.spec.selector}{"\n"}'
kubectl get pods -n "$LESSON_NS" --show-labels
kubectl describe service hello-systems -n "$LESSON_NS"
```

The `Endpoints:` line should be `<none>` or empty.

Try:

```bash
kubectl port-forward --pod-running-timeout=10s \
  -n "$LESSON_NS" service/hello-systems 18080:80
```

Expected failure shape:

```text
error: unable to forward port because ...
```

Exact wording varies. The evidence is “no selected backend,” not a container
crash.

Repair from the known-good declaration:

```bash
kubectl apply -f manifests/03-service.yaml
kubectl get endpointslice -n "$LESSON_NS" \
  -l kubernetes.io/service-name=hello-systems --watch
```

Stop once ready addresses reappear. This is a common production failure: model
server Pods are healthy, but a typo or inconsistent release label disconnects
them from traffic.

## Troubleshooting

Use this evidence ladder:

```text
1. get       Does the object exist? What is its summarized state?
2. describe  What conditions, ownership, configuration, and events explain it?
3. events    What recently happened?
4. logs      What did the application write?
5. logs -p   What did the previous crashed container write?
6. exec      What does the process see inside its namespaces?
7. -o yaml / jsonpath
             What exact API fields does automation need?
```

Common commands:

```bash
kubectl get all -n "$LESSON_NS"
kubectl describe deployment hello-systems -n "$LESSON_NS"
kubectl logs -n "$LESSON_NS" deployment/hello-systems \
  --all-pods=true --prefix
kubectl events -n "$LESSON_NS" --types=Warning
kubectl get deployment hello-systems -n "$LESSON_NS" \
  -o jsonpath='{.spec.replicas}{" desired, "}{.status.availableReplicas}{" available\n"}'
```

`kubectl get all` does not literally return every API kind. It is a convenient
workload overview, not a complete inventory.

### Image pull failure

Symptom: `ImagePullBackOff`.

```bash
kubectl describe pod -n "$LESSON_NS" <pod-name>
kubectl events -n "$LESSON_NS" --types=Warning
```

Check network access to `registry.k8s.io`, image spelling, and tag. Do not “fix”
it by switching to `latest`.

### Pod stays Pending

```bash
kubectl describe pod -n "$LESSON_NS" <pod-name>
kubectl get nodes
```

Read `FailedScheduling` messages. Lesson 07 teaches resource and constraint
diagnostics in depth.

### Port-forward says address already in use

Another process owns local port 18080. Choose another:

```bash
kubectl port-forward -n "$LESSON_NS" service/hello-systems 28080:80
curl http://127.0.0.1:28080/hostname
```

### Object is in the wrong namespace

```bash
kubectl get pod --all-namespaces | grep hello-systems
```

Do not solve this by habitually using `--all-namespaces` for changes. Find the
object, then target its exact namespace.

## Lab outline

1. Validate access to a local cluster.
2. Inspect and server-validate object YAML.
3. Create and examine a standalone Pod.
4. Prove that an unowned Pod is not recreated.
5. Create a Deployment and trace Deployment → ReplicaSet → Pod ownership.
6. Delete a managed Pod and observe reconciliation.
7. Scale desired state and re-apply the declared state.
8. Create a ClusterIP Service and inspect its EndpointSlice.
9. Break the Service selector while keeping Pods healthy.
10. Repair from the known-good manifest and run automated verification.

## Evidence to collect

Store local evidence only if it contains no sensitive cluster data:

```bash
mkdir -p evidence/lesson-05
kubectl get deployment,replicaset,pod,service,endpointslice \
  -n "$LESSON_NS" -o yaml > evidence/lesson-05/objects.yaml
kubectl get events -n "$LESSON_NS" \
  --sort-by='.metadata.creationTimestamp' > evidence/lesson-05/events.txt
kubectl get pods -n "$LESSON_NS" --show-labels \
  > evidence/lesson-05/pod-labels.txt
```

In `evidence/lesson-05/report.md`, explain:

- the old and replacement Pod names/UIDs;
- which controller recreated the Pod;
- the broken selector and labels it failed to match;
- why healthy Pods did not imply a reachable Service; and
- the desired-state and observed-state fields you inspected.

Do not commit kubeconfig content, tokens, cloud account identifiers, internal
addresses, or credentials.

## Exercises

Complete these before opening `exercises/SOLUTIONS.md`.

### Exercise 1 — label queries

Write selectors that return:

1. all web component Pods;
2. Pods whose version is either `v1` or `v2`; and
3. Pods that do not have the label `debug`.

### Exercise 2 — scale through YAML

Change only `spec.replicas` in a temporary copy of the Deployment to 2. Apply
it, observe reconciliation, then restore 3 without `kubectl scale`.

### Exercise 3 — distinguish deletion mechanisms

Delete the ReplicaSet, watch resources, and explain why Pods may terminate and
new ones appear. Identify which controller restores each object.

### Exercise 4 — fix an unknown selector issue

Ask a partner to change either one Service selector value or one Pod-template
label. Diagnose it using `get`, `describe`, and EndpointSlice output.

### Stretch — rollout mechanics

Change a Pod-template annotation:

```bash
kubectl patch deployment hello-systems -n "$LESSON_NS" \
  --type=merge \
  -p '{"spec":{"template":{"metadata":{"annotations":{"lesson/revision":"two"}}}}}'
kubectl rollout status deployment/hello-systems -n "$LESSON_NS"
kubectl get replicasets -n "$LESSON_NS"
```

Explain why changing the Pod template creates a new ReplicaSet even though the
image did not change. Restore the checked-in manifest afterward.

## Verification

Restore known-good declarations, then run:

```bash
kubectl apply -f manifests/02-deployment.yaml
kubectl apply -f manifests/03-service.yaml
./scripts/verify.sh
```

The script checks:

- the namespace exists;
- the Deployment has exactly 3 desired, updated, and available replicas;
- the Service selector is correct;
- the Service has three ready EndpointSlice addresses; and
- HTTP through a temporary port-forward returns a Pod hostname.

## Completion gate

You pass when `./scripts/verify.sh` succeeds and you can answer:

1. Why does deleting a managed Pod create a differently named replacement?
2. Which controller manages Pods directly for this Deployment?
3. Why can a Service be broken while all containers are healthy?
4. What is the difference between `spec` and `status`?
5. When would you choose `describe` over `logs`?
6. Why is an owner reference different from a label selector?

## Cleanup

Delete the complete lesson namespace:

```bash
./scripts/cleanup.sh
```

The script accepts `kind-llm-lab` by default and verifies the namespace's course
labels before deleting it. If you deliberately used a different disposable
context, repeat the explicit opt-in used for preflight:

```bash
ALLOW_NON_LAB_CONTEXT=1 ./scripts/cleanup.sh
```

Manual equivalent:

```bash
kubectl config current-context
kubectl get namespace llm-systems --show-labels
kubectl delete namespace llm-systems \
  --ignore-not-found --wait=true --timeout=120s
```

If this was a dedicated local cluster created only for these lessons, you may
delete it after all local lessons:

```bash
kind delete cluster --name llm-lab
# or
minikube delete --profile llm-lab
```

Never delete a shared cluster.

## Primary references

Only upstream project documentation is used:

- [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/)
- [Kubernetes objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/)
- [Declarative object management](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/)
- [Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [ReplicaSets](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/)
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Labels and selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
- [Owners and dependents](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/)
- [`kubectl` command reference](https://kubernetes.io/docs/reference/kubectl/)
- [`agnhost` upstream source](https://github.com/kubernetes/kubernetes/tree/master/test/images/agnhost)

Reference review date: 2026-10-21.
