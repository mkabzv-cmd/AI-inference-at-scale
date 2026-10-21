# Model Profiles

[`model-profiles.yaml`](model-profiles.yaml) is the course-wide model-selection
record. It separates two ideas that are easy to confuse:

- a **compute profile** describes available hardware, such as one 24 GB GPU;
- a **model profile** describes the model size and the provenance fields that
  must be frozen before an experiment.

The tiny Transformers and GGUF defaults are fully pinned because many lessons
need a common, affordable reference. Larger profiles deliberately do not invent
a revision. The learner must resolve the selected repository to an immutable
commit, review its license and files, and record its measured memory use before
starting GPU nodes.

When a lesson needs a different model, copy the required fields into that
lesson's experiment record. Do not edit this shared file with credentials,
private repository names, account identifiers, or local cache paths.
