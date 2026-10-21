# Lesson 05 exercise solutions

Try the exercises before reading this file.

## Exercise 1 — label queries

All web components:

```bash
kubectl get pods -n llm-systems \
  -l app.kubernetes.io/component=web
```

Version `v1` or `v2` uses a set-based selector:

```bash
kubectl get pods -n llm-systems \
  -l 'app.kubernetes.io/version in (v1,v2)'
```

Pods without a `debug` label:

```bash
kubectl get pods -n llm-systems -l '!debug'
```

## Exercise 2 — scale through YAML

Make a throwaway copy:

```bash
cp manifests/02-deployment.yaml /tmp/lesson-05-deployment.yaml
```

Edit `/tmp/lesson-05-deployment.yaml`, change `replicas: 3` to `replicas: 2`,
then:

```bash
kubectl apply -f /tmp/lesson-05-deployment.yaml
kubectl rollout status deployment/hello-systems -n llm-systems
kubectl get pods -n llm-systems \
  -l app.kubernetes.io/name=hello-systems
kubectl apply -f manifests/02-deployment.yaml
```

The ReplicaSet controller removes or creates Pods until the observed matching
count reaches the desired count.

## Exercise 3 — delete the ReplicaSet

```bash
kubectl get replicasets -n llm-systems
kubectl delete replicaset -n llm-systems \
  -l app.kubernetes.io/name=hello-systems
kubectl get deployment,replicaset,pod -n llm-systems --watch
```

With normal cascading deletion, deleting the ReplicaSet also deletes its owned
Pods. The Deployment controller observes that its revision lacks a suitable
ReplicaSet and creates one. The new ReplicaSet creates three Pods. Exact timing
can make transitions overlap.

## Exercise 4 — unknown selector issue

Use this evidence chain:

```bash
kubectl get pods -n llm-systems --show-labels
kubectl get service hello-systems -n llm-systems -o yaml
kubectl describe service hello-systems -n llm-systems
kubectl get endpointslice -n llm-systems \
  -l kubernetes.io/service-name=hello-systems -o yaml
```

Compare every Service selector key/value with Pod labels. Restore known-good
files rather than applying an undocumented one-off repair:

```bash
kubectl apply -f manifests/02-deployment.yaml
kubectl apply -f manifests/03-service.yaml
```
