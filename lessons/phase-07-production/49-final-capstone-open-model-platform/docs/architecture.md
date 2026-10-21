# Reference architecture

This is a logical architecture. Replace product names only after recording the
decision in the ADR and keeping the same trust and evidence boundaries.

```mermaid
flowchart LR
  Caller[Authenticated caller] -->|authorized request| Gateway[Private identity gateway]
  Gateway -->|tenant + trace context| API[Private model API]
  API --> Scheduler[Engine scheduler]
  Scheduler --> GPU1[GPU worker 1]
  Scheduler -. three-node path .-> GPU2[GPU worker 2]
  Scheduler -. three-node path .-> GPU3[GPU worker 3]
  API -->|optional| Retriever[Retrieval service]
  Retriever --> Index[(Versioned private index)]
  Registry[(Digest-pinned image)] --> API
  ModelStore[(Pinned model/tokenizer)]
  AdapterStore[(Hashed optional adapter)]
  ModelStore --> GPU1
  AdapterStore --> GPU1
  Eval[Frozen evaluation set] --> Gates[Release gates]
  API --> Telemetry[Logs, metrics, traces]
  GPU1 --> Telemetry
  GPU2 --> Telemetry
  GPU3 --> Telemetry
  Telemetry --> Gates
  Gates --> GitOps[Immutable environment pointer]
  GitOps --> API
```

The one-GPU path removes GPU workers 2 and 3 and all collectives. The
three-node path retains the same public API and release contract, but adds
rank/world-size configuration, rendezvous, topology evidence, collective
health, and worker-loss recovery.

The gateway is a trust boundary, not a label. The model Service remains
`ClusterIP`; an implementation must prove anonymous denial, authenticated but
unauthorized denial, and one authorized action before attaching restricted
content. NetworkPolicy narrows connectivity but does not replace caller
authentication or tenant authorization.

The telemetry path intentionally reaches every gate. A release cannot claim a
latency objective without raw workload evidence, recovery without a timestamped
failure timeline, or cleanup without an after-inventory.
