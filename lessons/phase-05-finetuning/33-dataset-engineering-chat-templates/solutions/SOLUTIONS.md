# Lesson 33 solution notes

## Assistant-only masking

The rendered system and user bytes receive label `-100`, the conventional
ignore index used by many cross-entropy implementations. The assistant content
and its message suffix receive labels equal to their input byte IDs. The
assistant role marker is masked: the task is to learn the response, not to spend
loss on predicting the fixed prefix.

This course path uses bytes only to make the transformation dependency-free.
Later training must use the exact model tokenizer. Token IDs from different
tokenizer revisions are not interchangeable.

## Deterministic split

The split is computed from SHA-256 of the checked-in seed and stable example ID.
It is independent of input ordering. Adding a new example does not reshuffle
existing examples. Changing the seed intentionally changes membership and
therefore creates a new evaluation contract.

## Duplicate and leakage boundary

The builder rejects repeated IDs and exact normalized message hashes before
splitting. The auditor rejects any ID or content hash repeated across processed
splits. This catches exact duplication, not semantic paraphrases. A production
pipeline needs task-specific near-duplicate, source-family, temporal, and entity
leakage policies.

## Packing trade-off

Greedy packing can reduce unused slots, but concatenating examples without
position, attention, or boundary handling can let one example attend to
another. Higher utilization is not automatically a valid training
configuration.
