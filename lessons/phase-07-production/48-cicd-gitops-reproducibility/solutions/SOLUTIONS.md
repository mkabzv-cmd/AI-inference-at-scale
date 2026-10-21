# Lesson 48 solution notes

## Release unit

The deployable unit is not only an image. The contract binds source revision,
image digest, model and tokenizer revisions, adapter/base compatibility, index
version/digest, configuration digest, and evidence digests. Promotion moves this
whole compatibility set.

## Metadata versus behavior

The regression candidate is structurally valid and all of its declared evidence
fields say pass. Its runtime smoke response is unsafe and misses required
concepts. This demonstrates why schema/provenance and behavioral tests are
separate gates.

## Promotion safety

The local pointer uses compare-and-swap: the caller states the release it
expects to replace. Unexpected drift blocks the write. A temporary file, fsync,
and atomic replace avoid a partially written state file.

## Rollback

The failed candidate reaches staging only. Production remains on the known-good
release. Staging is then explicitly promoted back to the good contract with the
regression as its expected current value, and the history retains both
transitions.
