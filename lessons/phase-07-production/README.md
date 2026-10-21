# Phase 7 — Production and LLMOps

Phase 7 turns model experiments into an observable, bounded, secure,
reproducible service lifecycle. All five lessons are practical drafts with
dependency-free CPU paths, machine-readable evidence, deliberate failures,
solutions, and optional private Kubernetes/GPU extensions.

| Lesson | Practical outcome | Main checked artifacts |
|---|---|---|
| [45 — Observability, load, and capacity](45-observability-load-capacity/) | Correlate requests across queue, prefill, decode, service, Pod, and node layers; find saturation under stepped load | loopback simulator, load generator, raw records, SLO analyzer, dashboard/rules/collector configs |
| [46 — Autoscaling and reliability](46-autoscaling-reliability/) | Compare static, misleading CPU, and queue-aware scaling; design cold-start, backpressure, drain, and recovery controls | autoscaling simulator, stable/unstable studies, HPA/KEDA/private workload templates, failure drill |
| [47 — Security and governance](47-security-governance/) | Bind artifact provenance, threat-model trust boundaries, reject unsafe Kubernetes exposure, and define an auth release gate | provenance builder/verifier, tamper drill, restricted workload, policy, threat/auth templates |
| [48 — CI/CD, GitOps, and reproducibility](48-cicd-gitops-reproducibility/) | Promote one immutable compatibility contract, prove runtime behavior, contain a staging regression, and roll back | release schema/candidates, atomic environment pointers, private GitOps rendering, smoke service/gate |
| [49 — Final open-model platform capstone](49-final-capstone-open-model-platform/) | Integrate pinned model, serving, optional adapter/RAG, evaluation, SLOs, access controls, promotion, rollback, cost, and verified teardown | capstone schema/templates, diagrams/runbook/ADR/threat model, exact evidence index, strict verifier, passing/failing fixtures |

Recommended order:

```text
45 measure -> 46 control capacity -> 47 establish trust boundaries
          -> 48 promote immutable releases -> 49 integrate and hand off
```

The checked CPU paths prove teaching mechanics and failure detection. They do
not claim that Docker builds, GPU engines, EKS workloads, identity gateways,
autoscalers, observability backends, GitOps controllers, or cloud teardown were
executed. Those extensions require your own private environment, immutable
artifacts, cost/credential controls, and observed evidence. Keep Services
private until the intended authentication and authorization gate has proved
anonymous and unauthorized denial.

Lesson 49 makes that honesty boundary machine-readable: its synthetic fixture
can pass structural validation but can never satisfy the operator-only
completion command. A live capstone qualifies only after another operator can
reproduce, validate, observe, recover, roll back, and completely remove the
selected platform.
