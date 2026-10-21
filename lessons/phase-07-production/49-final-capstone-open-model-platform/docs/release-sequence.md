# Promotion, recovery, and teardown sequence

```mermaid
sequenceDiagram
  actor Operator
  participant CI
  participant Registry
  participant GitOps
  participant Cluster
  participant Observe as Observability

  Operator->>CI: Submit reviewed source + release inputs
  CI->>CI: Static, schema, policy, unit, and fixture gates
  CI->>Registry: Publish immutable image/artifacts
  CI->>GitOps: Create private candidate pointer
  GitOps->>Cluster: Reconcile candidate
  Cluster->>Observe: Emit request, engine, GPU, Pod, and node evidence
  Operator->>Cluster: Verify anonymous and unauthorized denial
  Operator->>Cluster: Run frozen quality/load suites
  Operator->>Cluster: Inject bounded failure
  Cluster->>Observe: Record degradation and recovery
  Operator->>GitOps: Promote only if all gates pass
  Operator->>GitOps: Roll back to known-good release
  GitOps->>Cluster: Reconcile known-good release
  Operator->>Cluster: Run post-rollback smoke and denial checks
  Operator->>Cluster: Execute explicit teardown steps
  Operator->>Observe: Verify endpoint removal, workload stop, and released GPU capacity
  Operator->>CI: Finalize cleanup inventory and evidence index
```

A production promotion should be a pointer change to an already verified
immutable release. Rebuilding during rollback creates a new artifact and is not
a rollback. The rollback target must be known before the failure drill.

Teardown is also a controlled change. Capture an inventory before removal, run
scoped cleanup commands, wait for asynchronous cloud deletion, capture the
after-inventory, and investigate every residual resource. “`kubectl delete`
returned zero” is not sufficient evidence that node groups, volumes, load
balancers, object versions, or log-retention costs are gone.
