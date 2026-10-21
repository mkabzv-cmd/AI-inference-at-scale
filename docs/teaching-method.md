# Teaching Method

The course is built around mechanism and evidence.

## The recurring loop

```text
predict -> run -> measure -> explain -> change one variable -> re-measure -> clean up
```

Every lab begins with a prediction. This prevents the learner from treating
configuration as magic and gives failed predictions educational value.

## Spiral progression

The same domain task, benchmark schema, and evaluation set should evolve across
the entire course:

1. Serve the base model.
2. Compare runtimes.
3. Optimize the runtime.
4. Distribute the model.
5. Fine-tune an adapter.
6. Serve and benchmark the adapter.
7. Add retrieval.
8. Compare base, tuned, RAG, and tuned+RAG systems.
9. Operate the evidence-backed winner.

## Required depth

Each lesson must include:

- an execution-flow or architecture diagram;
- memory, communication, scheduling, or loss arithmetic where applicable;
- one controlled experiment;
- one intentional failure;
- evidence collection;
- mandatory cleanup.

## What not to teach

- Console screenshots as the main procedure.
- Unpinned `latest` images or model revisions.
- “Enable this flag because it is faster” without mechanism and measurement.
- Performance results without output-quality checks.
- Kubernetes abstractions before the learner understands the generated objects.
- Expensive hardware where a small model demonstrates the same mechanism.
