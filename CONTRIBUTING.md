# Contributing

This course values reproducibility and explanation over the number of tutorials.

## Before authoring a lesson

1. Read `docs/teaching-method.md`.
2. Start from `templates/lesson/`.
3. Pin primary documentation and record the validation date.
4. Select the cheapest hardware profile capable of demonstrating the mechanism.
5. Define the acceptance evidence before writing the walkthrough.

## Required lesson qualities

- The learner predicts an outcome before running commands.
- The lab changes one important variable at a time.
- Raw results are machine-readable.
- Performance claims include a correctness or quality gate.
- A failure is intentionally introduced and diagnosed.
- Cleanup is explicit, idempotent, and verified.
- No private environment identifiers or credentials appear in examples.

## Pull-request checklist

- [ ] Lesson metadata and prerequisites are accurate.
- [ ] Model, tokenizer, dataset, image, and dependency revisions are pinned.
- [ ] Commands work from a clean environment.
- [ ] Expected output is abbreviated rather than copied from huge logs.
- [ ] Cost and cleanup warnings are visible before resource creation.
- [ ] `make validate` passes.
- [ ] `make test-cpu` passes when the change affects an offline fixture.
- [ ] A second learner completed the lesson.

## Style

Use plain language first, then introduce the precise technical term. Explain the
mechanism behind configuration flags. Avoid unexplained “best practices” and
avoid claiming that one engine or configuration is universally fastest.
