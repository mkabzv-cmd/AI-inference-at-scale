# Lesson 42 solution notes

The component report is evidence about this corpus, query set, implementation,
and machine only. The “best” method may differ by metric and query family.
Inspect per-query rankings before changing a global weight.

Sparse retrieval should be strong when a query repeats source terms or exact
identifiers. The hashing-dense baseline can behave differently because word
and character features collide and are normalized. Reciprocal rank fusion uses
rank positions, so incomparable BM25 and dense score scales do not need to be
calibrated first.

The transparent reranker is intentionally not called a cross encoder. It sees
the query and chunk tokens together but has no learned parameters. Its purpose
is to expose candidate-width and feature-weight mechanics. The optional cross
encoder is a separate, pinned experiment.

A qrel that marks an unauthorized chunk relevant is invalid for a tenant-aware
task. Otherwise the evaluation would reward the retriever for violating its
security contract.
