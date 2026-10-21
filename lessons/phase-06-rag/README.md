# Phase 6 — Retrieval-augmented generation

Phase 6 builds a traceable knowledge system from first principles. All five
lessons are detailed drafts with local CPU labs; optional model, container, and
Kubernetes paths require the learner’s own reviewed environment.

The phase uses one coherent synthetic corpus and carries stable source,
version, chunk, tenant, and citation identities from ingestion through the
deployed API:

```text
architecture decision
        -> versioned ingestion/index
        -> sparse+dense+hybrid+reranked retrieval
        -> bounded grounded answers and security tests
        -> private knowledge-service capstone
```

| Lesson | Practical outcome |
|---|---|
| [40 — RAG vs tuning vs context](40-rag-vs-finetuning-long-context/) | Make an inspectable adaptation decision with hard constraints, weighted assumptions, and an ADR |
| [41 — Ingestion and indexes](41-ingestion-chunks-embeddings-indexes/) | Build an idempotent, versioned, licensed, tenant-aware corpus with stable chunks, exact vectors, ANN candidate experiments, hashes, and lineage |
| [42 — Hybrid retrieval and reranking](42-retrieval-hybrid-reranking/) | Implement BM25-style sparse, dense, RRF hybrid, and transparent reranking paths; evaluate recall, MRR, nDCG, latency, and tenant isolation |
| [43 — Grounding, evaluation, and security](43-grounded-generation-rag-evaluation-security/) | Assemble bounded untrusted context, cite exact spans, abstain, separate retrieval/answer metrics, and block cross-tenant, injection, and forged-citation paths |
| [44 — Knowledge-system capstone](44-capstone-knowledge-system/) | Run a private local API, a strict base/tuned/RAG/tuned-plus-RAG study, corpus update/rollback proof, and optional digest-pinned Kubernetes deployment |

## Recommended sequence

Run every mandatory CPU lab in order:

```bash
cd lessons/phase-06-rag/40-rag-vs-finetuning-long-context
./scripts/run-cpu-lab.sh

cd ../41-ingestion-chunks-embeddings-indexes
./scripts/run-cpu-lab.sh

cd ../42-retrieval-hybrid-reranking
./scripts/run-cpu-lab.sh

cd ../43-grounded-generation-rag-evaluation-security
./scripts/run-cpu-lab.sh

cd ../44-capstone-knowledge-system
./scripts/run-cpu-lab.sh
```

Later lesson runners rebuild the artifacts they consume, so a stale local
index cannot silently satisfy a test. Generated evidence remains ignored under
each lesson’s `artifacts/` directory.

## Phase completion evidence

Keep:

- lesson 40 decision results and ADR;
- corpus/index manifests and exact source-to-chunk lineage;
- checked-in qrels plus four retrieval-method reports and failure analysis;
- grounded claim/source mappings, abstention results, and adversarial tests;
- capstone API result, metrics excerpt, four-variant contract study, and
  v1→v2→v1 rollback proof;
- immutable image identities, rendered manifests, live cluster evidence, and
  cleanup records only if optional deployment work was actually run.

The CPU four-variant capstone uses clearly labeled deterministic behavior
proxies for base/tuned comparisons. It does not claim results from a real base
model or fine-tuned adapter. Replace those proxies after lesson 39 with exact
model/adapter revisions and re-run the same acceptance contract.

## Safety boundary

The corpus is synthetic. Do not substitute private documents until source
ownership, licensing, classification, tenant policy, retention, deletion,
embedding storage, model data transfer, and incident response are approved.
Retrieved content remains untrusted. Tenant filtering happens before ranking
and generation. The optional Kubernetes baseline is ClusterIP-only,
default-deny, non-root, read-only, and digest-pinned, but still requires real
authentication and authorization before handling sensitive data.
