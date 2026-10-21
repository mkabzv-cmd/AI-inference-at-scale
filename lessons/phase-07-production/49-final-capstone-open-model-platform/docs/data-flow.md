# Data and artifact flow

```mermaid
flowchart TD
  Source[Reviewed source commit] --> Build[Reproducible build]
  Build --> Image[Container image digest]
  Base[Base model revision] --> Adapt[Optional adapter training]
  Data[Frozen dataset revision] --> Adapt
  Adapt --> Adapter[Adapter bytes + hash]
  Corpus[Authorized corpus revision] --> Ingest[Optional deterministic ingestion]
  Ingest --> Index[Index bytes + hash]
  Image --> Contract[Release contract]
  Base --> Contract
  Adapter --> Contract
  Index --> Contract
  Eval[Frozen evaluation cases] --> Quality[Quality and safety evidence]
  Contract --> Candidate[Private candidate]
  Candidate --> Perf[Load and capacity evidence]
  Candidate --> Sec[Auth, policy, provenance evidence]
  Candidate --> Rel[Failure and rollback evidence]
  Candidate --> Cost[Budget evidence]
  Quality --> Promote{All gates pass?}
  Perf --> Promote
  Sec --> Promote
  Rel --> Promote
  Cost --> Promote
  Promote -->|yes| Pointer[GitOps environment pointer]
  Promote -->|no| Reject[No promotion]
  Pointer --> Teardown[Explicit teardown]
  Teardown --> Cleanup[After-inventory + zero unintended billable capacity]
```

Dataset permissions and deletion requirements must follow derived adapters,
indexes, caches, snapshots, logs, and backups. A SHA-256 hash identifies bytes;
it does not grant a license, prove authorship, or establish authorization.

Prompts and retrieved documents are untrusted input. Do not place raw prompts,
credentials, personal data, or restricted document text in unrestricted logs.
Record bounded identifiers, timings, token counts, policy decisions, and
redacted failure context.
