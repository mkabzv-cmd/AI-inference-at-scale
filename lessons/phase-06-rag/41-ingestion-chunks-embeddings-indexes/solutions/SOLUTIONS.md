# Lesson 41 solution notes

The checked-in fixture should produce one or more chunks for every section and
the same byte-for-byte output on repeated builds. If IDs change without a
source, version, chunking configuration, or algorithm change, the pipeline has
lost determinism.

For the metric exercise, all stored vectors and query vectors are L2
normalized. Dot product therefore equals cosine similarity. Squared Euclidean
distance is `2 - 2 × dot`, so all three metrics produce the same ordering even
though L2 sorts ascending.

The approximate path is intentionally allowed to lose recall. Its LSH bucket
selection is a candidate-generation experiment, not a production ANN claim.
Record candidate count and recall against exact search before considering a
faster index useful.

The invalid corpus should be rejected as a unit. Silently dropping the
proprietary record would create a partial index whose manifest no longer
represents the requested source snapshot.
