# Phase 1 — Kubernetes and EKS

Learn reconciliation, configuration, health, networking, scheduling, storage,
packaging, and debugging by rebuilding the one-GPU endpoint.

All lessons in this phase are runnable drafts:

| Lesson | What you learn and run |
|---|---|
| [05 — Objects and reconciliation](05-kubernetes-objects-reconciliation/) | Create a disposable local cluster; use Pods, Deployments, ReplicaSets, Services, labels, selectors, ownership, and events |
| [06 — Configuration, health, and request flow](06-configuration-health-request-flow/) | Build a small server; deploy ConfigMaps and Secrets; exercise startup, readiness, and liveness probes; trace DNS and endpoints |
| [07 — Resources and GPU scheduling](07-resources-gpu-scheduling/) | Measure requests and limits; use labels, taints, affinity, and topology; diagnose Pending workloads; verify a real EKS GPU |
| [08 — Model artifacts, storage, and caches](08-model-artifacts-storage-caches/) | Compare image, `emptyDir`, PVC, and node-cache lifecycles; provision EBS-backed storage safely |
| [09 — Packaging, releases, and debugging](09-packaging-releases-debugging/) | Convert raw manifests into a Helm chart; render, install, upgrade, break, diagnose, and roll back a release |
| [10 — One-GPU API capstone](10-capstone-one-gpu-api/) | Build and operate the complete EKS inference API from source through cleanup |

`draft` means the teaching text and practical files exist. Static CI does not
prove the local-cluster, Helm, GPU, or EKS paths; complete each lesson's
preflight, verification, and cleanup in your own lab environment.

Lessons 05 and 06 deliberately use a local CPU cluster so you can learn the
control plane without paying for a GPU. The EKS/GPU path begins only after those
mechanics are visible.
