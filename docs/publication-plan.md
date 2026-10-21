# Publication Plan

Keep the complete roadmap visible while publishing only validated lessons.

## Current authored state

Lessons 00–49 contain runnable drafts. Static checks cover document structure,
lesson metadata, shell and Python syntax, JSON validity, relative links,
executable scripts, practical-file presence, and high-confidence credential
patterns. CI also runs the aggregate offline CPU fixture and deliberate-failure
suite with `make test-cpu`, without installing third-party Python packages.
Every lesson remains `draft` until its relevant local, container, GPU,
distributed, and EKS paths have been completed from clean environments.

Passing CI is not runtime validation. CI does not currently build lesson images,
render every Helm chart, apply Kubernetes manifests, download models, exercise
GPUs, call EKS, or verify cloud cleanup. Record those results in the lesson's
validation metadata before promoting it.

There are no remaining outline-only lessons. `draft` still means author
validation rather than clean-environment publication.

## v0.1 — First useful system

Lessons 00–16. A learner can understand a request, use one GPU, operate basic
Kubernetes objects, and compare serving engines fairly.

## v0.2 — Systems depth

Lessons 17–31. A learner can explain major inference optimizations and conduct a
distributed-inference study on ordinary G-series networking.

## v0.3 — Model adaptation

Lessons 32–44. A learner can fine-tune an adapter, evaluate and serve it, add
retrieval, and decide between tuning and RAG.

## v1.0 — Operable platform

Lessons 45–49 plus validated capstones, contributor documentation, automated
checks, and reproducible environment profiles.

## Publication labels

- `outline`: objectives and lab contract exist, implementation not validated.
- `draft`: runnable implementation exists, author validation only.
- `review`: a second learner is testing the lesson.
- `published`: completed from a clean environment by at least two people.
- `refresh-needed`: upstream versions changed or checks failed.
