# Reproducibility checklist

- [ ] Study question and falsifiable hypothesis are written before results.
- [ ] Model revision and image digest are immutable.
- [ ] Live vLLM/Ray versions match the frozen software versions.
- [ ] Max model length, max sequences, and cache size match the frozen spec.
- [ ] License/access review is recorded.
- [ ] Workload bytes and SHA-256 are preserved.
- [ ] Node instance type, identities, zones, and GPU count are recorded.
- [ ] PyTorch, CUDA, NCCL, Ray, KubeRay, and vLLM versions are recorded.
- [ ] Network transport is supported by logs.
- [ ] Every response passed the correctness gate.
- [ ] Failed and excluded runs remain disclosed with reasons.
- [ ] At least two independent runs exist per strategy.
- [ ] Run order and cache state are documented.
- [ ] Raw samples remain available.
- [ ] Capacity start/end and price assumption are preserved.
- [ ] Failure/recovery timeline is preserved.
- [ ] Namespace and node-group cleanup are proven.
- [ ] Shared artifacts are sanitized without deleting scientific provenance.
