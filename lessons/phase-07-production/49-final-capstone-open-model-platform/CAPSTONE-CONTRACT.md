# Capstone contract

The machine-readable root of a submission is `contract.json`. It binds one
project, environment, immutable release, serving topology, and exact file
inventory. `capstone.schema.json` documents the public shape; the standard
library verifier in `src/verify_capstone.py` applies the cross-file rules that a
JSON Schema cannot express.

There are two validation modes:

- `fixture` is reserved for the checked-in synthetic verifier exercise. It may
  prove that controls reject bad evidence, but it cannot qualify a live
  release.
- `operator-run` means a named operator collected evidence from the selected
  environment. Every required gate must use `origin: observed`, and the final
  verifier must be invoked with `--require-operator-run`.

The only accepted serving topologies are `one-gpu` and `three-node`. A
three-node entry means three separately scheduled GPU workers and must include
distributed-process, network, and recovery evidence. It does not imply NVLink,
EFA, or InfiniBand. For the model-splitting path, `TP × PP = 3` and `DP = 1`.
The built-in manifest renderer intentionally supports only `one-gpu`; a
three-node submission must provide a reviewed engine-specific distributed
manifest and explicit topology/worker-count annotations.

The immutable release binds:

1. source commit and digest-pinned container image;
2. base model and tokenizer revisions;
3. serving configuration and frozen evaluation dataset hashes;
4. optional adapter hash plus its base-model revision;
5. optional RAG corpus/index hash and version;
6. six required gates: quality, performance, security, reliability, cost, and
   cleanup;
7. a known-good rollback release.

`evidence-index.json` is an exact allowlist. Every declared file is hashed, no
undeclared file is accepted, symlinks are rejected, and the release repeats the
hash of each gate's evidence. This creates two independent checks: the evidence
file must be the expected bytes, and it must be the evidence named by the
release.

The verifier can detect inconsistencies, missing evidence, unresolved markers,
unsafe Kubernetes shapes, mutable references, leaked credential patterns, and
claims whose declared origin conflicts with validation mode. It cannot prove
that a human did not lie. Review, signed provenance, protected CI, runtime
policy, and independent reproduction remain necessary.
