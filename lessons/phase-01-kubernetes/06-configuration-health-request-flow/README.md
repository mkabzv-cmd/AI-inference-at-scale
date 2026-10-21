# 06 — Configuration, health, and request flow

**Status:** draft
**Estimated time:** 6–8 hours
**Compute profile:** local CPU Kubernetes cluster
**Estimated GPU-minutes:** 0
**Prerequisites:** lesson 05; `kubectl`; `curl`; a local image builder
available to the cluster (`docker` for kind/Docker Desktop or Minikube's image
builder)
**Static review:** 2026-10-21; shell, Python, JSON, and YAML syntax checked and
application endpoints exercised locally; a complete cluster runtime pass is
still required

## Why this matters

Large-model servers do not become useful the instant their process starts. They
may spend minutes loading tokenizer files, mapping weights into host memory,
allocating GPU memory, compiling kernels, capturing CUDA graphs, and warming
caches.

Those facts produce three different questions:

1. **Startup:** has initialization completed at least once?
2. **Readiness:** should this Pod receive new requests right now?
3. **Liveness:** is the process stuck in a state only a restart can repair?

Using one probe for all three is dangerous. A liveness check that fails during a
normal ten-minute model load creates an endless restart loop. A readiness check
that restarts the process turns temporary overload into downtime. No readiness
check sends traffic to an instance whose weights are not loaded.

Configuration creates similar traps. A ConfigMap is not a secret store. A
Secret's base64 representation is not encryption. Environment variables and
mounted files update differently. This lesson makes all of that observable with
a small real HTTP server before GPUs and model weights make experiments slow.

## What you will build

You will build a local container image from `app/server.py`, then deploy:

```text
ConfigMap --------------------> environment at process start
     \------------------------> projected file, read per request

Secret -----------------------> read-only projected token file

kubelet on the Pod's Node
   |---- startup probe -------> /health/startup
   |---- readiness probe -----> /health/ready
   \---- liveness probe ------> /health/live

client Pod -> cluster DNS -> Service -> ready EndpointSlice -> app Pod :8080
```

The app also exposes `/stream`, which emits five short chunks. That gives later
inference lessons a concrete bridge to streamed token responses.

## Files in this lesson

```text
06-configuration-health-request-flow/
├── README.md
├── Dockerfile
├── app/
│   └── server.py
├── manifests/
│   ├── 00-namespace.yaml
│   ├── 01-configmap.yaml
│   ├── 02-secret.example.yaml
│   ├── 03-deployment.yaml
│   ├── 04-service.yaml
│   └── 05-dns-client.yaml
├── failures/
│   └── startup-probe-wrong-path.json
├── exercises/
│   └── SOLUTIONS.md
└── scripts/
    ├── build-load.sh
    ├── cleanup.sh
    ├── preflight.sh
    └── verify.sh
```

Run commands from this directory:

```bash
cd lessons/phase-01-kubernetes/06-configuration-health-request-flow
```

## Learning outcomes

By the end, you can:

- decide whether non-sensitive configuration belongs in a ConfigMap and
  sensitive material belongs in a Secret or external secret system;
- explain why Kubernetes Secret values being base64-encoded does not encrypt
  them;
- inject configuration as environment variables and mounted files;
- predict which configuration changes reach a running process;
- calculate probe failure windows from period, timeout, and threshold fields;
- explain startup, readiness, and liveness probe responsibilities;
- prove that failed readiness removes a Pod from Service endpoints without
  restarting it;
- prove that failed liveness restarts a container without replacing the Pod;
- trace DNS → Service → EndpointSlice → Pod → container request flow;
- distinguish Service `port`, `targetPort`, named `containerPort`, and a local
  port-forward port;
- inspect logs, conditions, events, restart counts, DNS, and EndpointSlices; and
- diagnose an intentionally broken startup probe.

## Cost and safety

The lab needs only a local CPU cluster and a tiny image. It creates a
`ClusterIP` Service, never a public load balancer. The Secret contains an
explicitly non-production demo value.

Never copy a real API key into:

- a committed YAML file;
- a shell command that will remain in history;
- a chat message;
- an image layer;
- an ordinary ConfigMap; or
- evidence you plan to publish.

Real systems normally combine Kubernetes access controls with encryption at
rest and a managed secret workflow. This lesson demonstrates Kubernetes object
mechanics; it is not a complete production secret-management design.

## Under the hood

### Configuration objects

A ConfigMap and Secret are namespaced API objects containing key/value data.
They are separate from the container image, so the same image can run with
different configuration.

```text
API object                         inside container
----------                         ----------------
ConfigMap key APP_GREETING -----> environment variable
ConfigMap key message.txt ------> /etc/lesson/config/message.txt
Secret key api-token -----------> /var/run/secrets/lesson/api-token
```

Environment variables are assembled when kubelet creates the container. Editing
the source object does not rewrite the environment of an existing process.
Restart or replace the Pod to consume new environment values.

The Deployment maps the three intended environment keys explicitly with
`configMapKeyRef` instead of importing every ConfigMap key with `envFrom`. That
keeps the file-shaped `message.txt` key out of the process environment and makes
each dependency visible in review.

ConfigMap and Secret volumes are projected by kubelet and can update in an
existing Pod after propagation delay. Applications only notice if they re-read
the file. A process that reads a file once at startup still needs an application
reload or restart. A volume mounted with `subPath` does not receive these
automatic updates, which is one reason this lesson mounts the directory.

### Secrets are not magically secret

In a YAML or JSON response, Secret `data` values are base64-encoded so arbitrary
bytes fit the API representation:

```text
plain bytes -> base64 text -> API object
```

Base64 is reversible encoding:

```bash
# GNU/Linux:
printf 'hello' | base64 | base64 --decode

# macOS/BSD (run instead of the GNU/Linux line):
printf 'hello' | base64 | base64 -D
```

Confidentiality instead depends on controls such as:

- who can read Secrets through Kubernetes RBAC;
- whether API data is encrypted at rest;
- who can access etcd backups;
- whether a Pod/service account is allowed to mount the Secret;
- application logs and crash dumps;
- node and container isolation; and
- external secret-manager and rotation design.

This lesson mounts the token as a file instead of an environment variable.
Either can be exposed by an overly privileged actor, but files are easier to
scope to a path and rotate without placing values in the process environment.

### The three probes

All three probes in this lab are HTTP requests initiated by the **kubelet**
against the Pod IP and container port. They do not travel through the Service.

```text
container begins
      |
      v
startup probe runs; readiness and liveness are held back
      |
      | first success
      v
readiness and liveness begin independently
      |
      +-- readiness fails -> Pod Ready=False -> endpoint becomes unready
      |
      \-- liveness fails enough times -> kubelet restarts container
```

The baseline startup probe is:

```yaml
periodSeconds: 2
timeoutSeconds: 1
failureThreshold: 15
```

It allows roughly 30 seconds of failed checks before a restart
(`2 seconds × 15 failures`), ignoring small scheduling and request timing
differences. The app simulates an 8-second model load.

Probe meanings:

| Probe | Question | Failure effect |
|---|---|---|
| startup | Has this process completed initialization? | restart after threshold; liveness/readiness wait |
| readiness | Can it safely accept new work now? | mark unready; remove from ready backends |
| liveness | Is restart the correct recovery? | restart that container after threshold |

Liveness must test an invariant that a restart can repair. “The server is busy”
is usually readiness or load-shedding information, not liveness.

### Request flow

For a request made from `dns-client` to
`http://health-app.llm-health.svc.cluster.local/`:

```text
1. client resolver
      |
      | DNS query
      v
2. cluster DNS returns the Service ClusterIP
      |
      v
3. packet targets Service port 80
      |
      | node service-routing implementation selects a ready endpoint
      v
4. EndpointSlice address for a ready Pod, target port 8080
      |
      v
5. container process listening on 0.0.0.0:8080
```

The exact data plane varies. A cluster may implement Service routing with
iptables, IPVS, nftables, or eBPF-based networking. The stable Kubernetes API
contract is the Service and its endpoints, not one mandatory packet mechanism.

Port vocabulary in this lesson:

```text
laptop 18081 --port-forward--> Service port 80
                                      |
                                      | targetPort: http
                                      v
                         named containerPort http = 8080
                                      |
                                      v
                              Python listens :8080
```

`containerPort` is metadata and a named reference. It does not itself open a
firewall or publish traffic.

## Predict before running

Write down answers:

1. During the simulated 8-second startup, will liveness failures restart the
   container?
2. If readiness fails, will the Pod phase stop being `Running`?
3. If liveness fails, will the Pod UID change?
4. If a ConfigMap-backed environment value changes, will the current Python
   process see it?
5. If a ConfigMap-backed file changes, can the current process see it?
6. Does cluster DNS point directly to one Pod or to the Service ClusterIP?
7. Is the text in Secret `.data` encrypted merely because it looks unreadable?

## Prerequisites and preflight

Run:

```bash
./scripts/preflight.sh
```

Expected shape:

```text
current context: kind-llm-lab
node/... condition met
preflight passed
```

By default, the script accepts only `kind-llm-lab`. If you intentionally use
another disposable local cluster, inspect its context and opt in explicitly:

```bash
kubectl config current-context
ALLOW_NON_LAB_CONTEXT=1 ./scripts/preflight.sh
```

Inspect the actual application:

```bash
sed -n '1,280p' app/server.py
sed -n '1,120p' Dockerfile
```

The server uses only Python's standard library. Its image runs as numeric user
10001 and drops Linux capabilities in the Pod.

The Dockerfile keeps the readable base tag
`python:3.13.15-alpine3.23` and pins the corresponding multi-platform OCI index
digest. The DNS utility image is pinned the same way. Those digests were
resolved from Docker Hub and `registry.k8s.io` on 2026-10-21. A digest is the
immutable input; the tag is release documentation.

Build and load it into the local cluster runtime:

```bash
./scripts/build-load.sh
```

For kind, the script runs `docker build` then `kind load docker-image`. For
Minikube, it uses `minikube image build`. For another local cluster, it prints
the exact image name you must make visible to its container runtime.

The resulting `lesson06/health-app:0.1.0` name is deliberately a local build
handle with `imagePullPolicy: Never`, not a claim that the tag is registry
immutable. Record the running container's `.status.containerStatuses[].imageID`
with your evidence. Later ECR lessons push the application image and deploy its
registry digest.

Before the namespace exists, perform a client-side structural check:

```bash
kubectl apply --dry-run=client -f manifests/00-namespace.yaml
kubectl apply --dry-run=client -f manifests/01-configmap.yaml
kubectl apply --dry-run=client -f manifests/03-deployment.yaml
kubectl apply --dry-run=client -f manifests/04-service.yaml
kubectl apply --dry-run=client -f manifests/05-dns-client.yaml
```

The example Secret is intentionally omitted because Step 2 creates a disposable
value without storing it in the repository. The Deployment dry-run can succeed
even though the referenced Secret and local image do not yet exist; those are
runtime dependencies, not embedded objects.

## Step-by-step lab

### Step 1 — create namespace and ConfigMap

```bash
kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/01-configmap.yaml
kubectl get configmap health-app-config -n llm-health -o yaml
```

Now that the namespace exists, run the stronger server-side check:

```bash
kubectl apply --dry-run=server -f manifests/01-configmap.yaml
kubectl apply --dry-run=server -f manifests/03-deployment.yaml
kubectl apply --dry-run=server -f manifests/04-service.yaml
kubectl apply --dry-run=server -f manifests/05-dns-client.yaml
```

Server dry-run exercises API validation, defaulting, authorization, and
admission without storing these objects. It still does not prove that the local
image or referenced Secret exists.

Notice that the three scalar-looking strings and `message.txt` are all keys
under `.data`.

### Step 2 — create a safe demo Secret

Read the example shape, but do not apply a real credential from it:

```bash
sed -n '1,160p' manifests/02-secret.example.yaml
```

Create an explicitly fake local value without saving it in the repository:

```bash
kubectl create secret generic health-app-secret \
  --namespace llm-health \
  --from-literal=api-token='local-demo-token-not-a-real-secret' \
  --dry-run=client -o yaml |
  kubectl apply -f -
```

Inspect metadata and keys without printing the value:

```bash
kubectl describe secret health-app-secret -n llm-health
```

Expected shape:

```text
Type:  Opaque
Data
====
api-token:  34 bytes
```

Because this value is deliberately fake, decode it once to prove base64 is not
encryption:

On GNU/Linux:

```bash
kubectl get secret health-app-secret -n llm-health \
  -o jsonpath='{.data.api-token}' | base64 --decode
printf '\n'
```

On macOS/BSD, use `-D` instead:

```bash
kubectl get secret health-app-secret -n llm-health \
  -o jsonpath='{.data.api-token}' | base64 -D
printf '\n'
```

Never perform this demonstration with production credentials or capture it in
published evidence.

### Step 3 — deploy while watching startup

Open a watch first:

```bash
kubectl get pods -n llm-health --watch
```

In a second terminal:

```bash
kubectl apply -f manifests/03-deployment.yaml
kubectl apply -f manifests/04-service.yaml
```

Watch the `READY` column remain `0/1` during startup, then become `1/1`.
`STATUS` can be `Running` while readiness is still false.

Inspect probe events and conditions:

```bash
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl get pod -n llm-health \
  -l app.kubernetes.io/name=health-app \
  -o jsonpath='{range .items[0].status.conditions[*]}{.type}={.status}{"\n"}{end}'
```

Follow structured logs:

```bash
kubectl logs -n llm-health deployment/health-app --follow
```

Stop after `server_listening` and probe access records appear.

### Step 4 — call every application endpoint

Start a local tunnel:

```bash
kubectl port-forward -n llm-health service/health-app 18081:80
```

In another terminal:

```bash
curl --fail --silent http://127.0.0.1:18081/
curl --fail --silent http://127.0.0.1:18081/config
curl --fail --silent http://127.0.0.1:18081/secret-fingerprint
curl --no-buffer http://127.0.0.1:18081/stream
```

Expected shapes:

```json
{
  "greeting": "hello from a ConfigMap",
  "model": "educational-model-v1",
  "pod": "health-app-...",
  "uptime_seconds": 12.3
}
```

```text
token-1
token-2
token-3
token-4
token-5
```

The secret endpoint returns only a short hash prefix and
`"token_exposed": false`; applications should not echo credentials.

Stop the port-forward with `Ctrl-C`.

### Step 5 — observe environment versus volume updates

Patch two ConfigMap keys:

```bash
kubectl patch configmap health-app-config -n llm-health \
  --type=merge \
  -p '{"data":{"APP_GREETING":"updated greeting","message.txt":"The mounted file changed.\n"}}'
```

Forward again and poll `/config`:

```bash
kubectl port-forward -n llm-health service/health-app 18081:80
```

In another terminal:

```bash
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  date
  curl --silent http://127.0.0.1:18081/config
  sleep 10
done
```

The mounted file should eventually show the new text. Propagation is not an
instantaneous API promise.

Now call `/`:

```bash
curl --silent http://127.0.0.1:18081/
```

The existing process still has the old `APP_GREETING` environment value.
Restart the Deployment:

```bash
kubectl rollout restart deployment/health-app -n llm-health
kubectl rollout status deployment/health-app -n llm-health --timeout=120s
```

After the new Pod is ready, `/` reports `updated greeting`. Restore the declared
configuration and restart once more:

```bash
kubectl apply -f manifests/01-configmap.yaml
kubectl rollout restart deployment/health-app -n llm-health
kubectl rollout status deployment/health-app -n llm-health --timeout=120s
```

### Step 6 — trace DNS and Service endpoints

Create a diagnostic client:

```bash
kubectl apply -f manifests/05-dns-client.yaml
kubectl wait --for=condition=Ready pod/dns-client \
  -n llm-health --timeout=120s
```

Resolve short and fully qualified names:

```bash
kubectl exec -n llm-health dns-client -- nslookup health-app
kubectl exec -n llm-health dns-client -- \
  nslookup health-app.llm-health.svc.cluster.local
```

Expected shape includes the Service ClusterIP from:

```bash
kubectl get service health-app -n llm-health \
  -o jsonpath='{.spec.clusterIP}{"\n"}'
```

Inspect endpoint membership:

```bash
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o wide
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o yaml
```

Make an in-cluster request from Python in the app container:

```bash
kubectl exec -n llm-health deployment/health-app -- \
  python -c 'import urllib.request; print(urllib.request.urlopen("http://health-app/").read().decode())'
```

This goes through Service DNS and the Service, even if the chosen backend is the
same Pod.

## Deliberate failure

Run all three experiments. They alter only the lesson namespace.

### Failure A — readiness fails, but the process stays alive

Record Pod UID and restart count:

```bash
kubectl get pod -n llm-health \
  -l app.kubernetes.io/name=health-app \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,RESTARTS:.status.containerStatuses[0].restartCount'
```

Create the file the app interprets as temporary unavailability:

```bash
kubectl exec -n llm-health deployment/health-app -- \
  touch /tmp/lesson-not-ready
sleep 6
kubectl get pods -n llm-health
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o yaml
```

Expected:

- Pod phase remains `Running`;
- readiness becomes `0/1`;
- restart count does not increase;
- the endpoint has `conditions.ready: false`; and
- Service traffic has no ready backend because there is one replica.

Repair without restart:

```bash
kubectl exec -n llm-health deployment/health-app -- \
  rm /tmp/lesson-not-ready
kubectl wait --for=condition=Ready pod \
  -l app.kubernetes.io/name=health-app \
  -n llm-health --timeout=30s
```

This models an inference server temporarily draining, overloaded, or unable to
admit more requests.

### Failure B — liveness fails and kubelet restarts the container

```bash
kubectl exec -n llm-health deployment/health-app -- \
  touch /tmp/lesson-kill-liveness
kubectl get pods -n llm-health --watch
```

After enough failed liveness checks, `RESTARTS` increases. The Pod name and UID
stay the same because the kubelet restarted a container within the Pod.
The new container filesystem no longer contains the trigger file.

Inspect both generations:

```bash
kubectl logs -n llm-health deployment/health-app
kubectl logs -n llm-health deployment/health-app --previous
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
```

Wait for readiness to return after the simulated startup:

```bash
kubectl wait --for=condition=Ready pod \
  -l app.kubernetes.io/name=health-app \
  -n llm-health --timeout=60s
```

### Failure C — the startup probe can prevent progress forever

Patch the Deployment's startup path to a nonexistent endpoint:

```bash
kubectl patch deployment health-app -n llm-health \
  --type=json \
  --patch-file failures/startup-probe-wrong-path.json
kubectl get pods -n llm-health --watch
```

Because `maxUnavailable: 0`, the old ready Pod can remain available while the
new broken revision fails startup. This is why `kubectl get pods` may show two
Pods during a one-replica rolling update.

Inspect the new Pod:

```bash
kubectl get replicasets,pods -n llm-health
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl events -n llm-health --types=Warning
```

Look for startup probe HTTP 404 failures and container restarts. Readiness and
liveness do not begin until startup succeeds.

Repair from the known-good file:

```bash
kubectl apply -f manifests/03-deployment.yaml
kubectl rollout status deployment/health-app \
  -n llm-health --timeout=120s
```

## Troubleshooting

### `ErrImageNeverPull`

The manifest intentionally says `imagePullPolicy: Never`. This makes the lab
fail loudly if you forgot to load the locally built image.

```bash
./scripts/build-load.sh
kubectl delete pod -n llm-health \
  -l app.kubernetes.io/name=health-app
```

The ReplicaSet creates a new Pod after the image is present.

### Pod says the Secret is missing

```bash
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl get secret health-app-secret -n llm-health
```

Create the demo Secret from Step 2. Secret and Pod must be in the same
namespace.

### Pod is Running but not Ready

```bash
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl logs -n llm-health deployment/health-app
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o yaml
```

Read probe status and app logs. Do not delete random Pods until you understand
whether startup is simply incomplete.

### DNS lookup fails

```bash
kubectl exec -n llm-health dns-client -- cat /etc/resolv.conf
kubectl exec -n llm-health dns-client -- nslookup kubernetes.default
kubectl get pods -n kube-system
kubectl get service health-app -n llm-health
```

If `kubernetes.default` also fails, inspect cluster DNS. If only `health-app`
fails, check its namespace and name.

### DNS works, request fails

```bash
kubectl get service health-app -n llm-health -o yaml
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o yaml
kubectl get pods -n llm-health --show-labels
```

Check selector, ready endpoints, Service `port`, `targetPort`, and the
application listening address/port.

### Probe debugging trap

Do not test only from your laptop. Kubelet probes target the Pod IP and port,
not your port-forward. Compare:

```bash
kubectl describe pod -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl logs -n llm-health deployment/health-app
```

## Lab outline

1. Build and load a real local image.
2. create non-secret and secret configuration;
3. watch startup hold readiness and liveness back;
4. call configuration, fingerprint, and streaming endpoints;
5. compare live updates of a mounted file with fixed process environment;
6. trace cluster DNS, Service, EndpointSlice, Pod port, and app listener;
7. fail readiness without a restart;
8. fail liveness and observe a container restart;
9. break startup and diagnose a stalled rollout; and
10. restore declarations and verify the complete system.

## Evidence to collect

Create an evidence directory only if its contents are safe to publish:

```bash
mkdir -p evidence/lesson-06
kubectl get deployment,pod,service,endpointslice -n llm-health -o yaml \
  > evidence/lesson-06/objects.yaml
kubectl get events -n llm-health \
  --sort-by='.metadata.creationTimestamp' \
  > evidence/lesson-06/events.txt
kubectl logs -n llm-health deployment/health-app \
  > evidence/lesson-06/application.log
```

Do **not** export the Secret object.

Write a report containing:

- a startup/readiness/liveness timeline;
- Pod UID and restart counts before/after each failure;
- EndpointSlice readiness before/during/after readiness failure;
- the Service and Pod ports;
- DNS lookup output with private/internal addresses redacted if needed;
- why the environment value and mounted file behaved differently; and
- a request-flow diagram.

## Exercises

Complete these before opening `exercises/SOLUTIONS.md`.

### Exercise 1 — calculate failure windows

For each probe, calculate the approximate continuous-failure interval before
Kubernetes acts. Explain why the actual wall-clock value is approximate.

### Exercise 2 — design model-server probes

Write probe policies for a server that:

- takes up to 12 minutes to load;
- can temporarily stop admitting requests under pressure; and
- exposes a deadlock detector that only a restart repairs.

Explain, do not merely provide YAML.

### Exercise 3 — add a second replica

Scale to two replicas. Make one unready by executing directly into one named
Pod. Prove the Service retains one ready endpoint and continues serving.

### Exercise 4 — cross-namespace DNS

Create a temporary client Pod in `default`. Show why `health-app` alone does not
resolve there, then use `health-app.llm-health` and the full name.

### Exercise 5 — Secret rotation observation

Change the demo Secret, wait for the projected file to update, and show that the
fingerprint changes without printing the token. Explain why an application that
caches the token at startup would behave differently.

## Verification

Restore declarations:

```bash
kubectl apply -f manifests/01-configmap.yaml
kubectl apply -f manifests/03-deployment.yaml
kubectl apply -f manifests/04-service.yaml
kubectl rollout restart deployment/health-app -n llm-health
kubectl rollout status deployment/health-app -n llm-health --timeout=120s
```

Then:

```bash
./scripts/verify.sh
```

The script confirms:

- the Deployment completed;
- the Pod is ready;
- exactly one ready endpoint exists;
- the ConfigMap environment value reached the app;
- the ConfigMap volume is readable;
- the Secret is consumed without being returned; and
- HTTP through the Service succeeds.

## Completion gate

You pass when verification succeeds and you can explain:

1. Why startup protects a slow model load from liveness.
2. Why readiness failure changes Service routing but not restart count.
3. Why liveness restart does not necessarily change Pod UID.
4. Why base64 does not provide Secret confidentiality.
5. Why a ConfigMap environment update requires a new container.
6. How `port: 80`, `targetPort: http`, and `containerPort: 8080` connect.
7. Why EndpointSlice is stronger evidence than “the Service exists.”

## Cleanup

```bash
./scripts/cleanup.sh
```

This deletes the namespace, including the demo Secret, ConfigMap, Deployment,
Service, EndpointSlice, and client Pod, then verifies deletion.

The script accepts `kind-llm-lab` by default and checks the namespace's course
labels before deleting it. For another intentionally selected disposable
context:

```bash
ALLOW_NON_LAB_CONTEXT=1 ./scripts/cleanup.sh
```

The local image may remain in Docker and the cluster runtime. Remove it only if
you no longer need it:

```bash
docker image rm lesson06/health-app:0.1.0
```

That command is optional and may fail while a local cluster still references
the image. Do not delete a shared cluster.

## Primary references

- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Encrypting confidential data at rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [Configure liveness, readiness, and startup probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Pod lifecycle and container probes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Debugging DNS resolution](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)
- [Accessing applications with port-forward](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [kind loading an image](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster)
- [Minikube image command](https://minikube.sigs.k8s.io/docs/commands/image/)
- [Docker Official Image for Python](https://hub.docker.com/_/python)
- [`agnhost` upstream source](https://github.com/kubernetes/kubernetes/tree/master/test/images/agnhost)

Reference review date: 2026-10-21.
