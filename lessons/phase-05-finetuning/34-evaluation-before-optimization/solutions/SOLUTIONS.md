# Lesson 34 solution notes

## Why the checked-in baseline fails

The fixture intentionally includes good and bad answers. It exercises required
concept coverage, forbidden claims, per-slice aggregation, and a failed release
decision. A successful evaluator does not require a successful model.

## Why the gate is frozen before training

Changing a threshold, expected concept, decoding setting, or test example after
seeing the tuned model turns the acceptance set into a tuning set. The hash lock
makes changes visible. A legitimate contract revision receives a new version
and is reported separately; it does not rewrite the historical comparison.

## Why keywords are insufficient

The deterministic metric is inspectable and cheap, but it can reward keyword
stuffing and miss correct paraphrases. Review every failed and safety-critical
answer. Use human or model judges only with a versioned rubric, judge model,
prompt, variance study, and disagreement analysis.

## Correct interpretation

The baseline result answers: "How did these exact responses score under this
exact frozen contract?" It does not estimate universal Kubernetes competence.
The tiny set is a course mechanism, not a statistically representative
benchmark.
