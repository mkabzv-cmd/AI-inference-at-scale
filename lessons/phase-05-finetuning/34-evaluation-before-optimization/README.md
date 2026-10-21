# 34 — Evaluation before optimization

**Status:** draft
**Time:** 5–7 hours
**Compute:** `local-cpu`; optional `g1` serving endpoint
**GPU budget:** zero for fixtures; about 20 minutes for one endpoint evaluation
**Prerequisites:** 33
**Last reviewed:** 2026-10-21

## Why this matters

If you train first and decide what “better” means afterward, you can nearly
always find a favorable example. That is not evaluation. It is selection on the
answer.

Before fine-tuning, freeze the intended behavior, important failure slices,
decoding configuration, metrics, and release thresholds. Run the untouched base
model and keep its errors. Those errors tell you whether adaptation is needed
and provide the comparison for every later checkpoint.

This lesson builds a small but complete evaluation contract for the synthetic
operations domain introduced in lesson 33. It contains eight held-out prompts
covering GPU scheduling, health, cost cleanup, safe exposure, and
reproducibility. Each item declares concepts that should appear, claims that
must not appear, a slice, and a review note. A lock file fingerprints both the
acceptance JSONL, evaluation configuration, and evaluator implementation.

The required CPU path evaluates checked-in response fixtures. Some are
deliberately correct; others are dangerously wrong. The evaluator must succeed
as software while the model fixture fails release. This separation matters:

```text
pipeline correctness != model quality
```

The optional path calls any Phase-2 OpenAI-compatible chat endpoint with the
frozen decoding configuration. It saves raw responses before computing metrics,
so a future reviewer can audit what actually happened.

## Learning outcomes

By the end, you can:

- write an intended-use-specific acceptance set before optimization;
- separate model responses, deterministic metrics, human review, and release
  decisions;
- freeze test examples and evaluation configuration with content hashes;
- explain why train, validation, and acceptance data have different roles;
- define slices that expose failures hidden by one aggregate score;
- set safety-critical slice gates before seeing tuned-model results;
- use deterministic concept and forbidden-claim checks without confusing them
  with semantic truth;
- preserve exact prompts, decoding settings, model identity, and raw outputs;
- explain seed, sampling, nondeterministic kernels, and serving scheduler
  variance;
- reject acceptance-set edits motivated only by a failing checkpoint.

## What you will build

The CPU lab produces:

- `base-results.json`: per-example concept coverage, missing concepts,
  forbidden hits, item pass/fail, slice summaries, total pass rate, and hashes
  of the exact acceptance, evaluation-config, evaluator, and raw-prediction
  files;
- `base-release-decision.json`: every predeclared gate, observed value, required
  value, and final decision;
- a verified lock check over the acceptance set, metric configuration, and
  evaluator code.

The checked-in base fixture intentionally fails. At the time this draft was
authored, it exercises both passing and failing examples and at least one
forbidden claim. The verifier checks those properties instead of hard-coding a
single score.

The optional endpoint path additionally produces raw JSONL predictions with
latency, model name returned by the server, and usage fields when available.
It then applies the same evaluator and gates without rewriting them.

## Files in this lesson

```text
34-evaluation-before-optimization/
├── README.md
├── acceptance.lock.json
├── configs/
│   ├── evaluation.json
│   └── release-gates.json
├── data/
│   ├── acceptance.jsonl
│   └── base-predictions.jsonl
├── results.schema.json
├── scripts/
│   ├── run-cpu-baseline.sh
│   ├── run-deliberate-failure.sh
│   ├── run-endpoint-evaluation.sh
│   └── verify_baseline.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── apply_gates.py
    ├── call_openai_endpoint.py
    ├── evaluate.py
    └── verify_lock.py
```

Generated evidence belongs under ignored `artifacts/`. The acceptance set,
lock, and gates are tracked because they define the comparison.

## Under the hood

### Evaluation is a versioned function

Think of one evaluation result as:

```text
result = evaluate(
    model artifact,
    tokenizer and chat template,
    acceptance examples,
    system prompt,
    decoding configuration,
    metric implementation,
    runtime,
)
```

Change any argument and you have a different experiment. A model ID alone is
not sufficient provenance. A mutable tag, changed tokenizer, new system prompt,
different `max_tokens`, altered stop sequence, or engine-specific sampling
behavior can change responses.

The lock in this lesson covers acceptance bytes and `evaluation.json`. A real
evaluation bundle should also record image digest, model revision, tokenizer
revision, endpoint engine/version, request payloads, and hardware/runtime
metadata.

### Required terms and forbidden claims

The evaluator normalizes response text with Unicode NFKC, lowercasing, and
whitespace collapse. For each item:

```text
coverage = required concepts found / required concepts declared
item pass = coverage >= threshold AND forbidden hits == 0
```

This is deliberately inspectable. It can still be wrong. A response can repeat
all keywords in a false sentence. A correct paraphrase can miss literal
phrases. Morphology and multilingual answers can produce false negatives. One
special case accepts `endpoint` as a match for the concept `endpoints`, which
demonstrates that even a “deterministic” metric contains authored judgment.

Use these metrics as stable signals and triage aids, not as a substitute for
reviewing generative answers.

### Slices and aggregation

An overall average can hide a complete failure on rare but severe cases. The
course gates therefore include exact requirements for cost safety and exposure
safety. A model cannot compensate for advising public unauthenticated exposure
by answering several ordinary health questions correctly.

The slice sizes here are tiny. A 100% result on two examples has enormous
uncertainty and must not be generalized. The purpose is to learn the mechanism:
choose slices from a failure taxonomy, report their counts, and prevent a
weighted average from erasing high-severity regressions.

### Test data is not a debugging prompt library

Training data teaches parameters. Validation data supports choices such as
checkpoint selection or early stopping. A final acceptance set estimates the
chosen artifact under a frozen contract. Repeatedly inspecting acceptance
failures and editing training around individual items leaks test information
into development.

In a small educational project, complete separation is difficult. State every
exposure. For a real release, maintain a larger hidden or independently owned
test set and rotate it under a controlled process.

### Decoding and variance

The configuration uses temperature zero to reduce sampling variance. Zero
temperature does not promise bit-for-bit equality across engines, versions,
GPU kernels, batching schedules, quantization methods, or numerical precision.
Some servers ignore unsupported seed fields. Continuous batching can alter
execution order. Greedy ties can break differently.

For stochastic evaluation, run repeated trials and report a distribution with
the exact seeds. Do not pick the best seed. For deterministic task metrics,
separate response variance from metric determinism.

### Judge models

A model judge can evaluate semantics that keyword metrics miss, but it adds
another model, prompt, decoding policy, bias, failure surface, and cost. If you
add one, freeze the rubric and judge revision, blind it to model identity,
measure repeatability, compare against human labels, and retain disagreement
examples. Never treat “the judge returned 8.4” as ground truth without this
work.

## Prerequisites and preflight

Run from this directory:

```bash
cd lessons/phase-05-finetuning/34-evaluation-before-optimization
python3 --version
python3 -m json.tool acceptance.lock.json >/dev/null
python3 -m json.tool configs/evaluation.json >/dev/null
python3 -m json.tool configs/release-gates.json >/dev/null
```

Verify the frozen files:

```bash
python3 src/verify_lock.py \
  --lock acceptance.lock.json \
  --acceptance data/acceptance.jsonl \
  --config configs/evaluation.json \
  --evaluator src/evaluate.py
```

Read every acceptance item and gate before training:

```bash
sed -n '1,20p' data/acceptance.jsonl
python3 -m json.tool configs/release-gates.json
```

For the optional path, start or port-forward a Phase-2 engine privately and
verify it:

```bash
export MODEL_BASE_URL="http://127.0.0.1:8000"
export MODEL_ID="<exact-served-model-name>"
curl -fsS "$MODEL_BASE_URL/v1/models"
```

Do not point the script at a paid or production API accidentally. The runner
sends all eight prompts sequentially.

## Cost and safety

The fixture path is CPU-only and offline.

The optional path consumes eight model requests. On a self-hosted GPU, record
node start time and restore capacity after evaluation. On a metered API, inspect
pricing and request limits first. The included prompts contain no private data.

The endpoint defaults to a placeholder bearer value if no key is set, which is
appropriate only for a private unauthenticated local lab endpoint. Do not expose
that endpoint publicly. If the endpoint requires authentication, set
`OPENAI_API_KEY` through an approved secret mechanism and never commit it or
write it into evidence.

Some checked-in responses contain unsafe advice so the evaluator can detect it.
They are negative fixtures, not instructions.

## Predict before running

Create `artifacts/predictions.md`:

1. Can the evaluator pass while the model release fails?
2. Which checked-in responses contain explicitly forbidden claims?
3. Which slices should have zero tolerance under the supplied gate?
4. If one acceptance newline changes, should the lock still pass?
5. Does temperature zero guarantee identical results across vLLM, SGLang, and
   Transformers?
6. Could a response contain every required keyword and still be wrong?
7. Why must raw responses be kept instead of only aggregate scores?
8. What would make a model judge reproducible enough to add?

Do not revise the predictions after the run.

## Lab outline

1. Read and critique the intended-use acceptance contract.
2. Verify the frozen hashes.
3. Evaluate a mixed-quality base fixture.
4. Apply release gates and inspect why it fails.
5. Review errors by slice and failure type.
6. Deliberately mutate the acceptance bytes and observe lock failure.
7. Optionally evaluate a live one-GPU endpoint.
8. Propose a new contract version without rewriting the old one.

## Step-by-step lab

### 1. Inspect the acceptance set

Pretty-print one line:

```bash
sed -n '1p' data/acceptance.jsonl | python3 -m json.tool
```

For each item, ask whether the required terms are necessary, sufficient, or
neither. Identify the severity of its forbidden claims. If the prompt depends
on facts not contained in the question, note that the model must describe
evidence rather than invent current cluster state.

### 2. Run the frozen CPU baseline

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-baseline.sh
```

Expected shape:

```text
PASS: acceptance set and evaluation configuration match the lock
pass_rate=<fraction> forbidden_hits=<positive count>
release_decision=fail
PASS: frozen baseline produced mixed item results ...
```

The release failure is expected. The command itself returns zero because the
lesson is verifying that the decision machinery correctly rejects the fixture.
In CI promotion, use `apply_gates.py --require-pass` so a failed candidate exits
nonzero.

### 3. Inspect item and slice failures

```bash
python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("artifacts/base-results.json").read_text())
for item in result["per_example"]:
    if not item["pass"]:
        print(
            item["id"],
            item["slice"],
            "missing=", item["required_missing"],
            "forbidden=", item["forbidden_found"],
        )
print("slices", result["slices"])
PY
```

Read each raw response, not only its labels. Classify failures as omission,
unsafe assertion, factual error, task misunderstanding, verbosity, or metric
false positive/negative. Add categories rather than changing the acceptance
answer to favor the fixture.

### 4. Inspect the release decision

```bash
python3 -m json.tool artifacts/base-release-decision.json
```

Each check contains observed, required, and pass. Verify that an overall metric
cannot override a failed critical slice or forbidden-claim gate.

Demonstrate the CI behavior:

```bash
set +e
python3 src/apply_gates.py \
  --results artifacts/base-results.json \
  --gates configs/release-gates.json \
  --output artifacts/ci-decision.json \
  --require-pass
status=$?
set -e
test "$status" -ne 0
printf 'PASS: failed candidate blocks promotion\n'
```

### 5. Optional live endpoint

With a private endpoint running:

```bash
export MODEL_BASE_URL="http://127.0.0.1:8000"
export MODEL_ID="<exact-served-model-name>"
./scripts/run-endpoint-evaluation.sh
```

Inspect the raw file first:

```bash
sed -n '1,3p' artifacts/endpoint-predictions.jsonl
```

Then inspect results and decision. Record the image digest, model/tokenizer
revision, engine version, GPU, and endpoint startup flags in
`artifacts/endpoint-environment.md`. If the server ignores `seed`, record that
fact rather than claiming seeded reproducibility.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
cat artifacts/expected-lock-failure.txt
```

The script copies the acceptance file and adds one newline. Semantic examples
are unchanged, but exact bytes and SHA-256 differ. The lock rejects it.

This is intentionally strict. Byte-level locking makes every change visible.
If line endings or canonical serialization should be portable across systems,
define and version a canonicalization process, then lock its output. Do not
silently normalize after historical results exist.

Recovery is:

```bash
python3 src/verify_lock.py \
  --lock acceptance.lock.json \
  --acceptance data/acceptance.jsonl \
  --config configs/evaluation.json \
  --evaluator src/evaluate.py
```

Do not “recover” by replacing the hash with the mutated file merely because a
candidate model prefers it. A legitimate acceptance revision gets a new
contract name, lock, baseline result, and comparison notes.

## Verification

Run all CPU checks:

```bash
./scripts/run-cpu-baseline.sh
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/base-results.json >/dev/null
python3 -m json.tool artifacts/base-release-decision.json >/dev/null
```

Check coverage:

```bash
python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("artifacts/base-results.json").read_text())
decision = json.loads(
    Path("artifacts/base-release-decision.json").read_text()
)
assert result["examples"] == len(result["per_example"]) == 8
assert 0 < result["passed"] < result["examples"]
assert result["forbidden_hits"] > 0
assert decision["release"] is False
assert len(result["slices"]) == 5
print("PASS: result is complete and the unsafe baseline is blocked")
PY
```

For a live result, rerun at least once if you intend to claim determinism.
Compare raw response hashes and explain differences.

## Troubleshooting

If the lock fails before you intentionally edit anything, check line-ending
conversion, formatting tools, and uncommitted changes:

```bash
git diff -- data/acceptance.jsonl configs/evaluation.json acceptance.lock.json
```

Do not regenerate the lock until you understand the change.

If prediction IDs mismatch, the evaluator reports missing and extra IDs.
Partial evaluation must not be averaged as though the full set ran.

If every answer fails required terms despite looking correct, inspect
normalization and phrasing. Record metric false negatives; do not automatically
rewrite model responses or test expectations.

If the endpoint returns HTTP 400, inspect whether it supports `seed`,
`max_tokens`, and the OpenAI-compatible message shape. Any adapter you add to
remove unsupported fields becomes part of the evaluation configuration.

If an endpoint times out, preserve completed raw requests only if the output
format explicitly records incompleteness. The provided runner exits and does
not present a partial file as a full result.

If latency varies, remember that this lesson's sequential client does not
control server warmup, queueing, continuous batching, cache state, or other
requests. Performance benchmarking belongs to lesson 12; here latency is
diagnostic metadata.

## Evidence to collect

```text
artifacts/
├── predictions.md
├── base-results.json
├── base-release-decision.json
├── ci-decision.json
├── mutated-acceptance.jsonl
├── expected-lock-failure.txt
├── error-review.md
├── endpoint-predictions.jsonl        # optional
├── endpoint-results.json             # optional
├── endpoint-release-decision.json    # optional
├── endpoint-environment.md           # optional
└── report.md
```

`report.md` must state:

- intended use and excluded claims;
- contract and lock hashes;
- model/runtime identity;
- decoding configuration;
- aggregate and every slice count/rate;
- forbidden claims;
- manual review disagreements with deterministic metrics;
- known test exposure;
- release decision;
- what evidence would justify training.

Do not publish endpoint metadata containing private registry, cluster, or
account identifiers.

## Exercises

1. Add a correct paraphrase that the term metric misses and document the false
   negative.
2. Add keyword-stuffed nonsense that passes coverage and document the false
   positive.
3. Build a rubric-based human review sheet with blinded model labels.
4. Run five stochastic samples at a nonzero temperature and report per-item
   pass distributions instead of the best sample.
5. Add a latency field validation without turning this correctness set into a
   load benchmark.
6. Create `oms-operations-acceptance-v2` with a documented reason, then baseline
   the original model under both contracts.
7. Add a hidden challenge set owned by a peer and define when it may be opened.
8. Add confidence intervals appropriate to binary item results and explain why
   eight examples remain too small.
9. Compare the same model revision through two engines and investigate any
   response differences.
10. Design a judge-model experiment including rubric, judge version, repeated
    runs, human labels, and disagreement adjudication.

## Completion gate

You are done when:

- the locked fixture evaluation passes as a pipeline;
- the intentionally unsafe fixture fails release;
- you can explain every failed gate and review every raw failed response;
- mutation of one byte is detected;
- you can distinguish deterministic metric output from semantic truth;
- your proposed training objective is based on frozen failure evidence;
- optional endpoint results include complete model, tokenizer, engine, image,
  decoding, and hardware provenance;
- you commit to reporting the original acceptance result even if a later tuned
  checkpoint fails it.

## Cleanup

Remove generated local evidence only after retaining the approved report:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

If you ran a GPU endpoint, stop the Pod or process, delete its lesson namespace
if one was created, and restore the GPU node group to the capacity recorded
before the lab. Verify no model Service became public and no load balancer was
created.

Do not delete the tracked acceptance set, lock, or historical baseline simply
because it is inconvenient.

## Primary references

Sources were reviewed on 2026-10-21:

- [Hugging Face Evaluate documentation](https://huggingface.co/docs/evaluate/)
- [Hugging Face generation configuration](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)
- [HELM: Holistic Evaluation of Language Models](https://arxiv.org/abs/2211.09110)
- [Beyond Accuracy: Behavioral Testing of NLP Models with CheckList](https://aclanthology.org/2020.acl-main.442/)
- [Datasheets for Datasets](https://arxiv.org/abs/1803.09010)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The offline evaluator and fixtures are author-validated. No claim is made that
the tiny acceptance set measures broad Kubernetes competence or that a live GPU
model has passed it.
