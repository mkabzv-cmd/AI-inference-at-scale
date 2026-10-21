# Lesson 04 solutions

## Predictions

1. With no eligible GPU capacity, the Pod remains Pending and scheduler events
   explain the unsatisfied constraints.
2. No. A Pod is scheduled to one node. Distributed work uses multiple
   cooperating Pods/processes.
3. No. `ClusterIP` is internal virtual networking and creates no AWS load
   balancer.
4. A process can answer liveness while model loading or CUDA initialization is
   incomplete. It must not receive inference traffic until ready.
5. The rendered Deployment uses the ECR `@sha256:...` digest URI.

## Exercises

1. Deployment → ReplicaSet → Pod is controller ownership. Client →
   port-forward → Service → ready EndpointSlice/Pod → container port 8080 is
   request flow.
2. Decode iterations should roughly double, but first-token time should remain
   similar for the same prompt on a warm process. Small-model timing is noisy;
   compare repeated runs.
3. A non-matching selector leaves the Service with no ready endpoints.
   `kubectl get endpointslice -n "$LAB_NAMESPACE"` exposes this. Restore the
   selector and wait for endpoints before retesting.
4. The Deployment still desires one replica, so its Pod remains/reappears and
   cannot schedule. Costs may be zero after scale-down, but desired application
   state and cleanup evidence are wrong.
5. Protect counters with the existing lock or a separate lock, serialize a
   simple text/JSON response, and test initial values plus an increase after a
   request.
