# 40 — RAG vs fine-tuning vs long context

**Status:** draft
**Time:** 4–6 hours
**Compute:** `local-cpu`
**GPU budget:** none
**Prerequisites:** 34; lesson 39 is recommended for the full comparison
**Last reviewed:** 2026-10-21

## Why this matters

“Should we fine-tune or use RAG?” is usually the wrong first question. Prompting,
long context, retrieval, and parameter updates place information in different
parts of the system and fail differently.

- Prompting puts instructions and a small amount of information directly in
  every request.
- Long context puts a selected document set into the request without building a
  persistent retrieval service.
- Retrieval-augmented generation (RAG) finds a small evidence set at request
  time and adds it to the prompt.
- Fine-tuning changes model parameters or adapter parameters.
- RAG plus fine-tuning combines updateable evidence with learned behavior.

Fine-tuning can teach a response format, vocabulary, classification boundary,
or task behavior. It is generally a poor database for facts that change daily,
need per-user access filtering, or must be cited exactly. RAG can make current
sources visible, but it does not automatically teach the model to follow a
special format, retrieve the right chunk, resist malicious documents, or remain
faithful to evidence. Long context avoids an index for small one-off document
sets, but request cost and attention reliability change as the context grows.

This lesson turns those distinctions into an explicit, inspectable decision.
The supplied program applies hard requirements first and then a weighted
capability matrix. Its result is not “the answer.” It exposes assumptions so
you can challenge them, prototype the uncertain parts, and write an
architecture decision record (ADR).

## Learning outcomes

By the end, you can:

- separate a knowledge freshness gap from a behavior gap;
- explain where information resides in prompts, retrieved chunks, adapters, and
  base weights;
- compare update latency, citations, access filtering, request latency,
  training cost, and operational surface;
- identify when prompting should be attempted before adding infrastructure;
- identify when a small long-context solution is simpler than a persistent
  vector index;
- explain why RAG and fine-tuning can be complementary;
- define hard feasibility requirements separately from scored preferences;
- inspect every score contribution and change an assumption explicitly;
- write an ADR with prototype evidence, consequences, rollback, and a reversal
  condition;
- avoid presenting an authored decision matrix as measured fact.

## What you will build

You will run four scenarios through five candidate strategies:

```text
prompting
long_context
rag
finetuning
rag_plus_finetuning
```

The four fixtures are designed to produce different recommendations:

1. frequently updated, access-filtered policies with citations;
2. stable input-to-JSON behavior with low request overhead;
3. a one-off question over three supplied documents;
4. changing runbooks plus a learned incident-report format.

The result file contains feasibility, missing hard requirements, normalized
scores, and every criterion contribution. You will then replace one scenario
with your own capstone requirements and complete `ADR-TEMPLATE.md`.

You will also run a deliberate failure containing an undefined criterion. The
tool must stop rather than silently ignore a requirement it does not understand.

## Files in this lesson

```text
40-rag-vs-finetuning-long-context/
├── README.md
├── ADR-TEMPLATE.md
├── configs/
│   ├── broken-scenario.json
│   ├── scenarios.json
│   └── strategies.json
├── results.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   └── verify.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    └── decision_matrix.py
```

Generated decisions and your ADR working copy belong under ignored
`artifacts/`.

## Under the hood

### Four places information can enter

At inference, a decoder predicts next-token probabilities from its parameters
and input tokens. Prompt instructions and long-context documents are input
tokens. RAG also produces input tokens, but an external retrieval pipeline
selects them. Fine-tuning changes parameters before inference.

```text
                         offline
training examples -> optimizer -> base/adapter parameters
                                      |
caller -> prompt ---------------------+----> model -> answer
          ^
          |
query -> retriever -> filtered chunks
```

Parameter changes are compact at request time but slower and riskier to update.
Retrieved context is replaceable and traceable but consumes context tokens,
adds online latency, and creates another security boundary.

### Hard requirements before scoring

The decision tool first removes strategies that cannot meet declared hard
requirements. In the fixture, a strategy must explicitly support capabilities
such as citations, daily updates, per-request filtering, or learned behavior.
A high weighted score cannot rescue an infeasible strategy.

This prevents an average from hiding a must-have property. If every answer must
respect document entitlement, “usually good latency” cannot compensate for the
absence of a filtering boundary.

### Weighted assumptions

For each feasible strategy:

```text
weighted points = importance × authored capability
normalized score = sum(weighted points) / (sum(importance) × 5)
```

Both importance and capability use a zero-to-five scale. The numbers are not
benchmarks. For example, the file says long context has a small operational
surface for a one-off task, while RAG has stronger access filtering for a
repeated multi-user service. Your architecture, corpus size, provider,
latency target, and team ownership can change those values.

The program retains contributions so disagreement becomes specific: “I think
long context deserves a 2 rather than 5 for operational simplicity because our
gateway cannot accept large bodies,” not merely “I dislike the recommendation.”

### Failure modes by strategy

Prompting can be ignored, consume limited context, or become a brittle collection
of instructions. Long context can overflow limits, increase time to first
token, bury relevant evidence, and send unauthorized text if selection is
wrong.

RAG can fail in ingestion, chunking, embedding, index freshness, filtering,
candidate retrieval, reranking, context assembly, or generation. Retrieval
also turns documents into untrusted prompt input.

Fine-tuning can overfit, regress general behavior, memorize sensitive examples,
change style without improving facts, or become stale. It requires dataset and
checkpoint provenance and a rollback path.

The combined system can solve both behavior and knowledge requirements, but it
inherits both sets of failure modes and more operational ownership.

### Prototype before commitment

The cheapest feasible approach should get a controlled prototype. A prompt may
solve a behavior problem without training. Supplying three documents may beat
operating an index. Conversely, pasting thousands of documents into every
request may be more expensive and less reliable than retrieval.

The decision matrix narrows prototypes; measured acceptance results decide.

## Prerequisites and preflight

Run from this directory:

```bash
cd lessons/phase-06-rag/40-rag-vs-finetuning-long-context
python3 --version
python3 -m json.tool configs/strategies.json >/dev/null
python3 -m json.tool configs/scenarios.json >/dev/null
```

Read the criteria definitions and verify that each strategy contains every
criterion:

```bash
python3 - <<'PY'
import json
from pathlib import Path

doc = json.loads(Path("configs/strategies.json").read_text())
criteria = set(doc["criteria"])
for name, strategy in doc["strategies"].items():
    assert set(strategy["capabilities"]) == criteria, name
print("PASS: capability matrix is rectangular")
PY
```

Have your lesson-34 evaluation contract available. The chosen architecture must
eventually be tested against behavior, quality, security, latency, and cost
requirements—not only the matrix.

## Cost and safety

This lesson is offline and CPU-only.

Architecture decisions can still create later cost or security commitments.
RAG introduces storage, ingestion, indexes, online retrieval, and possibly an
embedding model. Fine-tuning introduces GPU training, checkpoints, datasets,
and model artifacts. Long context can sharply increase input tokens and prefill
work. Record those cost owners before prototyping.

Access filtering must happen before unauthorized text enters the model prompt.
Asking the model to “ignore documents the caller cannot see” is not
authorization. Fine-tuning private text can create memorization and deletion
obligations. Do not use the simple matrix as security approval.

## Predict before running

Create `artifacts/predictions.md`:

1. Which strategy should win for facts that change daily and require exact
   citations?
2. Which should win for a stable formatting behavior with no external facts?
3. Why might long context beat RAG for three one-off documents?
4. Which hard requirement forces the combined strategy in the final fixture?
5. Could a strategy with the highest raw score be rejected?
6. Which capability numbers do you already disagree with?
7. What measured prototype result would reverse each recommendation?
8. Does RAG guarantee grounded generation?

Keep predictions and add observations later.

## Lab outline

1. Classify each scenario as knowledge, behavior, or both.
2. Inspect hard requirements and authored capability scores.
3. Run and verify the four decision fixtures.
4. Trace one recommendation to criterion contributions.
5. Change one assumption and observe the ranking.
6. Run an undefined-criterion failure.
7. Add your capstone scenario.
8. Write an ADR with evidence and reversal conditions.

## Step-by-step lab

### 1. Run the reviewed fixtures

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected shape:

```text
daily-policy: rag
stable-json-style: finetuning
one-off-three-documents: long_context
fresh-knowledge-and-special-format: rag_plus_finetuning
PASS: hard constraints and weighted assumptions ...
```

The verifier checks fixture intent. It does not certify that those outcomes are
universally correct.

### 2. Inspect feasibility before rank

```bash
python3 - <<'PY'
import json
from pathlib import Path

doc = json.loads(Path("artifacts/decisions.json").read_text())
case = next(item for item in doc["results"] if item["id"] == "daily-policy")
for item in case["rankings"]:
    print(
        item["strategy"],
        "feasible=", item["feasible"],
        "score=", round(item["normalized_score"], 3),
        "missing=", item["missing_hard_requirements"],
    )
PY
```

Notice that scoring is still shown for infeasible options. That helps explain
trade-offs, but selection chooses the highest-ranked feasible option.

### 3. Trace one score

```bash
python3 - <<'PY'
import json
from pathlib import Path

doc = json.loads(Path("artifacts/decisions.json").read_text())
case = next(
    item for item in doc["results"]
    if item["id"] == "one-off-three-documents"
)
winner = next(
    item for item in case["rankings"]
    if item["strategy"] == case["recommendation"]
)
print(json.dumps(winner["contributions"], indent=2, sort_keys=True))
PY
```

Recalculate the numerator and denominator manually.

### 4. Change exactly one assumption

Copy the strategies under artifacts:

```bash
cp configs/strategies.json artifacts/my-strategies.json
```

Change only `long_context.capabilities.small_operations_surface` from `5` to
`1`, then rerun:

```bash
python3 src/decision_matrix.py \
  --strategies artifacts/my-strategies.json \
  --scenarios configs/scenarios.json \
  --output artifacts/changed-decisions.json
```

Explain whether the one-off recommendation changes. A changed result does not
prove the original was wrong; it proves that the assumption influenced the
choice.

### 5. Add your system scenario

Copy `configs/scenarios.json` under artifacts and add one scenario with:

- update frequency;
- behavior change needed;
- citation/provenance requirement;
- access-control model;
- latency and cost goals;
- operations ownership;
- hard requirements;
- your expected recommendation.

Run the matrix. If the tool and your expectation disagree, inspect
contributions before altering values.

### 6. Write the ADR

```bash
cp ADR-TEMPLATE.md artifacts/ADR.md
```

The ADR must name the smallest prototype for the top two feasible options and a
result that would reverse the decision. Reference the lesson-34 acceptance set
and add retrieval-specific tests that later lessons will implement.

## Deliberate failure

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-failure.txt
```

The broken scenario assigns importance to `telepathy`, which is not a declared
criterion. Ignoring it would create a plausible but incomplete decision. The
program exits nonzero.

Recovery requires either removing the accidental field or deliberately adding a
new criterion and a capability value for every strategy. A new criterion must
have a definition and evidence plan; do not add arbitrary columns merely to
force a preferred winner.

## Verification

Run:

```bash
./scripts/run-cpu-lab.sh
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/decisions.json >/dev/null
```

Then verify every recommendation is feasible:

```bash
python3 - <<'PY'
import json
from pathlib import Path

doc = json.loads(Path("artifacts/decisions.json").read_text())
for result in doc["results"]:
    selected = next(
        row for row in result["rankings"]
        if row["strategy"] == result["recommendation"]
    )
    assert selected["feasible"], result["id"]
print("PASS: no infeasible option was selected")
PY
```

Review your ADR separately. Code cannot verify that stakeholders, ownership,
privacy, deletion, or prototype evidence are complete.

## Troubleshooting

If the verifier reports an unexpected winner, inspect hard requirements first,
then contributions. Do not immediately edit `expected_recommendation`.

If no strategy is feasible, the program records no recommendation. This may be
the correct result: requirements conflict with available architecture. Propose
a new option or negotiate a requirement explicitly.

If a score changes after adding a criterion with zero importance, confirm that
the denominator includes only the scenario importance sum. Zero should have no
effect.

If your real requirement does not fit zero-to-five scoring, make it a hard
requirement or extend the tool. Examples include legal prohibition, data
residency, deletion deadlines, and an absolute latency ceiling.

If stakeholders disagree about capability values, assign evidence owners and
prototype the disagreement. The matrix is doing useful work by exposing it.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── decisions.json
├── changed-decisions.json
├── my-strategies.json
├── my-scenarios.json
├── expected-failure.txt
├── ADR.md
└── prototype-plan.md
```

Your ADR and prototype plan must include:

- task and users;
- knowledge sources and update rate;
- behavior requirements;
- data classification and caller entitlements;
- corpus size and context budget;
- model and tokenizer assumptions;
- latency, quality, safety, and cost gates;
- ownership for ingestion, training, serving, and incidents;
- rollback and deletion;
- a date or condition for revisiting the decision.

## Exercises

1. Add training lead time and index freshness lag as separate criteria.
2. Model a regulatory requirement that forbids sending documents to an external
   endpoint.
3. Add a scenario where prompting is sufficient and explain why training would
   be waste.
4. Calculate long-context input-token cost for a repeated workload and compare
   it with retrieval operations.
5. Add a maximum context constraint as a hard feasibility check based on
   measured token counts.
6. Design an experiment comparing long context with top-k retrieval on the same
   frozen questions.
7. Add a deletion requirement. Trace deletion from source, chunk, embedding,
   cache, checkpoint, and logs.
8. Explain why RAG does not automatically solve hallucination.
9. Explain why fine-tuning does not automatically make facts current.
10. Have another learner independently score the matrix and compare
    disagreements before seeing recommendations.

## Completion gate

You are done when:

- all fixture decisions and failure checks pass;
- you can trace a winner to both hard requirements and score contributions;
- you have changed one assumption and explained the effect;
- your capstone scenario separates behavior from knowledge needs;
- your ADR compares at least two feasible approaches;
- every recommendation has a prototype and reversal condition;
- access filtering, provenance, update, deletion, latency, and ownership are
  explicit;
- you can explain why the tool is an assumption ledger, not an oracle.

## Cleanup

This lesson creates no cloud or Kubernetes resources. Remove generated evidence
when finished:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

Keep an approved ADR in your own version-controlled project if it governs a
real system. Do not commit private architecture, corpus, or security details to
this public course repository.

## Primary references

Sources were reviewed on 2026-10-21:

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [Lost in the Middle: How Language Models Use Long Contexts](https://aclanthology.org/2024.tacl-1.9/)
- [Azure Architecture Center: Retrieval-augmented generation](https://learn.microsoft.com/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The decision program and fixtures are author-validated. Its capability scores
are intentionally editable assumptions and are not external performance data.
