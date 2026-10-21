# Lesson 06 exercise solutions

Attempt each exercise before reading its solution. Commands assume the lesson's
known-good resources are running in namespace `llm-health`.

## Exercise 1 — calculate failure windows

From `manifests/03-deployment.yaml`:

| Probe | Period | Failure threshold | Approximate continuous-failure window |
|---|---:|---:|---:|
| startup | 2 seconds | 15 | 30 seconds |
| readiness | 2 seconds | 2 | 4 seconds |
| liveness | 5 seconds | 2 | 10 seconds |

These are approximations, not timers with exact deadlines. The first check's
alignment, kubelet work, network timing, `timeoutSeconds`, and success/failure
transitions affect wall-clock observation.

Startup failure leads to a restart only after its threshold. Until startup first
succeeds, readiness and liveness are disabled. After startup succeeds, readiness
can change endpoint membership and liveness can restart the container.

## Exercise 2 — design model-server probes

One reasonable starting point:

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: http
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 78
readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 2
livenessProbe:
  httpGet:
    path: /health/live
    port: http
  periodSeconds: 15
  timeoutSeconds: 2
  failureThreshold: 3
```

The startup budget is about 13 minutes, slightly above the stated 12-minute
upper bound. The endpoint should become successful only after weights, runtime,
and required warm-up are genuinely complete.

Readiness can fail quickly when admission should stop. The server can recover
without losing loaded weights, so readiness must not restart it.

Liveness calls a narrow deadlock detector. Three failures over roughly 45
seconds reduce the chance that transient latency causes a destructive restart.
Production values must be measured from actual load and failure behavior.

## Exercise 3 — two replicas, one unready

```bash
kubectl scale deployment/health-app -n llm-health --replicas=2
kubectl rollout status deployment/health-app -n llm-health --timeout=120s
kubectl get pods -n llm-health \
  -l app.kubernetes.io/name=health-app
```

Select one exact Pod:

```bash
UNREADY_POD="$(kubectl get pods -n llm-health \
  -l app.kubernetes.io/name=health-app \
  -o jsonpath='{.items[0].metadata.name}')"
kubectl exec -n llm-health "$UNREADY_POD" -- \
  touch /tmp/lesson-not-ready
sleep 6
```

Inspect:

```bash
kubectl get pods -n llm-health \
  -l app.kubernetes.io/name=health-app
kubectl get endpointslice -n llm-health \
  -l kubernetes.io/service-name=health-app -o yaml
```

One Pod should be `0/1`, one `1/1`, and exactly one endpoint should have
`conditions.ready: true`. The Service continues routing to the ready Pod.

Repair and restore one replica:

```bash
kubectl exec -n llm-health "$UNREADY_POD" -- \
  rm /tmp/lesson-not-ready
kubectl scale deployment/health-app -n llm-health --replicas=1
kubectl rollout status deployment/health-app -n llm-health --timeout=120s
```

## Exercise 4 — cross-namespace DNS

Create a temporary client in `default`:

```bash
kubectl run lesson-06-dns-client \
  --namespace default \
  --image=registry.k8s.io/e2e-test-images/agnhost:2.53@sha256:99c6b4bb4a1e1df3f0b3752168c89358794d02258ebebc26bf21c29399011a85 \
  --command -- /agnhost pause
kubectl wait --for=condition=Ready pod/lesson-06-dns-client \
  -n default --timeout=120s
```

The short name is searched in the client's own namespace:

```bash
kubectl exec -n default lesson-06-dns-client -- \
  nslookup health-app
```

That should not resolve the `llm-health` Service. Namespace-qualified forms do:

```bash
kubectl exec -n default lesson-06-dns-client -- \
  nslookup health-app.llm-health
kubectl exec -n default lesson-06-dns-client -- \
  nslookup health-app.llm-health.svc.cluster.local
```

The cluster domain can be customized, so inspect `/etc/resolv.conf` rather than
assuming every cluster uses `cluster.local`.

```bash
kubectl delete pod lesson-06-dns-client -n default
```

## Exercise 5 — observe Secret rotation

Record only the application's fingerprint:

```bash
kubectl port-forward -n llm-health service/health-app 18081:80
curl --silent http://127.0.0.1:18081/secret-fingerprint
```

In another terminal, update the deliberately fake value:

```bash
kubectl create secret generic health-app-secret \
  --namespace llm-health \
  --from-literal=api-token='rotated-local-demo-value' \
  --dry-run=client -o yaml |
  kubectl apply -f -
```

Poll the fingerprint without printing the Secret:

```bash
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  curl --silent http://127.0.0.1:18081/secret-fingerprint
  sleep 10
done
```

The app reads the mounted file on every request, so the hash should eventually
change without a Pod restart. An application that cached the token during
startup would keep using the old value until it implemented reload behavior or
the Pod restarted.

Restore the lesson's fake starting value:

```bash
kubectl create secret generic health-app-secret \
  --namespace llm-health \
  --from-literal=api-token='local-demo-token-not-a-real-secret' \
  --dry-run=client -o yaml |
  kubectl apply -f -
```
