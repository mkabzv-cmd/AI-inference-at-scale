# OMS operations adapter

## Model details

This card accompanies a course-built adapter over the exact base and tokenizer
revisions recorded in `release-manifest.json`. The adapter is not a standalone
model. It must never be loaded over a similarly named but different base.

## Intended use

The intended use is an educational, human-reviewed assistant that explains
evidence-first Kubernetes GPU operations. It has no authority to mutate a
cluster. It is not approved for public unauthenticated service or private
operational data.

## Training data

The course run uses the synthetic `oms-operations-mini/1.0.0` contract from
lesson 33. The release embeds its data card and immutable manifest hash. A
private replacement needs its own review and card.

## Evaluation

Promotion requires the frozen `oms-operations-acceptance-v1` contract from
lesson 34. The tiny acceptance set is a pipeline and safety-slice exercise, not
evidence of general Kubernetes competence. Raw base and tuned responses,
release decisions, and known metric disagreements remain with the release.

## Limitations and risks

The training set is tiny, synthetic, English-only, narrow in domain, and
unsuitable for factual coverage claims. Generated commands can be wrong or
unsafe. Human review, authorization, private-by-default networking, audit
evidence, and independent cleanup checks remain mandatory.

## Reproducibility

The manifest records model/tokenizer revisions, dataset and training hashes,
adapter file hashes, card hashes, and artifact type. Serving and benchmark
evidence additionally record the immutable container digest, engine version,
flags, hardware, and decoding/workload contract.
