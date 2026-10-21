# 43 — Grounded generation, RAG evaluation, and security

**Status:** draft
**Time:** 8–10 hours
**Compute:** `local-cpu`; optional local model endpoint
**Prerequisites:** 41, 42
**Last reviewed:** 2026-10-21

## Why this matters

Retrieving a relevant chunk does not prove that an answer is supported. A
generator can ignore good evidence, combine incompatible statements, attach a
citation to the wrong claim, or confidently answer a question whose evidence
was never retrieved. Conversely, a correct-looking phrase can come from model
memory rather than the authorized source.

Retrieved text also crosses a security boundary. A web page, ticket,
spreadsheet, or uploaded document can contain instructions aimed at the model:
ignore the system policy, reveal secrets, call a tool, or send data elsewhere.
Those words are data from an untrusted source, not instructions. RAG does not
eliminate hallucination or prompt injection; it creates a system in which
evidence and failures can be observed and constrained.

This lesson keeps the verified path deterministic and CPU-only. It uses the
lesson-42 reranked retriever, assembles a bounded context, removes duplicate
overlap, blocks known injection fixtures, selects an extractive sentence,
maps the claim to exact source spans, cites it, and abstains below an explicit
threshold. The extractor is not offered as an LLM replacement. It is a testable
fallback that proves the safety and evaluation contract before an optional
model endpoint is introduced.

You will measure retrieval and answer behavior separately. You will also run
strict tests that fail if another tenant’s chunks appear, an injection chunk
enters context, or citation-shaped text cannot be mapped to supplied evidence.

## Learning outcomes

By the end, you can:

- explain why retrieval relevance, answer correctness, and faithfulness are
  distinct properties;
- assemble context in rank order under a word budget;
- remove duplicated sentences introduced by overlapping chunks;
- preserve chunk, document, version, source URI, and normalized source offsets;
- mark retrieved content as untrusted data;
- block a known indirect prompt-injection fixture before model input;
- generate deterministic extractive claims and explicit abstentions;
- map each claim and citation label to an exact quotation and source span;
- reject unknown citations and quotes absent from context;
- calculate retrieval hit/recall separately from answer phrase, abstention,
  and supported-claim metrics;
- prove that tenant filtering occurs before generation;
- distinguish a security regression test from a complete prompt-injection
  defense;
- place an optional OpenAI-compatible endpoint behind host and credential
  restrictions.

## What you will build

The safe request path is:

```text
authenticated identity in a real service
              |
              v
trusted tenant mapping
              |
              v
lesson-42 pre-filtered retrieval and reranking
              |
              v
known-injection scan --blocked--> audit evidence
              |
              v
ranked sentence deduplication + word budget
              |
              v
deterministic extractor or optional isolated model
              |
              v
claim -> citation label -> chunk -> source span validation
              |
              +--> supported answer
              `--> abstention
```

Seven evaluation questions include five answerable facts, an unsupported
personal-data request, and a cross-tenant request. A generated adversarial
snapshot adds a shared document containing explicit indirect prompt-injection
phrases. Security tests require it to be retrieved, recognized, blocked, and
absent from context.

The machine-readable result preserves:

- raw candidate chunk and document IDs;
- safe context and blocked chunks;
- context budget use;
- answer, abstention flag, and generator identity;
- claims, citation IDs, exact quotes, and source offsets;
- retrieval metrics and answer metrics in separate objects;
- cross-tenant, injection, and forged-citation outcomes.

## Files in this lesson

```text
43-grounded-generation-rag-evaluation-security/
├── README.md
├── configs/
│   ├── grounding.json
│   ├── optional-model-endpoint.json
│   ├── unsafe-remote-model-endpoint.json
│   └── unsafe-allow-injection.json
├── data/
│   ├── adversarial-documents.jsonl
│   ├── confounded-questions.json
│   ├── forged-answer.json
│   └── questions.json
├── results.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   ├── run-deliberate-failure.sh
│   └── verify.py
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── build_adversarial_corpus.py
    ├── grounding.py
    ├── openai_compatible_client.py
    └── security_tests.py
```

The runner invokes lessons 41 and 42, then writes only generated evidence
under ignored `artifacts/`.

## Under the hood

### Retrieval is necessary but not sufficient

For an answerable question, this lesson records:

```text
retrieval_hit = any(relevant_chunk in top_k)
retrieval_recall@k = relevant chunks returned / relevant chunks labeled
```

The answer evaluator separately checks expected phrases, correct abstention,
and claim support. A relevant candidate with a wrong extracted sentence is a
generation/selection failure. A correct expected phrase with no relevant
evidence is not a grounded success.

The checked-in phrases are deterministic fixture assertions, not a complete
semantic answer judge. Real evaluation requires human rubrics, multiple valid
references, model-assisted judges validated against people, and failure
sampling. Keep the component boundary even when the judge becomes richer.

### Context order, deduplication, and budget

Candidates arrive in reranked order. For each authorized candidate, the
assembler:

1. scans the text for configured injection indicators;
2. splits it into whole sentences;
3. skips a normalized sentence already present from an overlapping chunk;
4. adds whole sentences while the configured word budget permits them;
5. assigns a local citation label such as `S1`;
6. preserves source identity and normalized character offsets.

Word count is only a transparent proxy for tokenizer length. A model-backed
system must use the deployed tokenizer and reserve tokens for system
instructions, the question, output, tool schemas, and safety framing.

Ordering is an experiment variable. Highest-score-first can privilege a
duplicate source; grouping by source can reduce variety; chronological order
can matter for policy updates. Record the rule and test it. This baseline uses
rank order and exact-sentence deduplication so both are visible.

### Claims and citations

An answer such as:

```text
Tokens expire after twelve hours and must not be shared. [S1]
```

contains a claim object with:

```text
claim text
  -> S1
  -> stable chunk ID
  -> document ID and version
  -> source URI
  -> normalized source_start_char/source_end_char
  -> exact quote
```

The validator requires the citation label to exist in supplied context, the
chunk IDs to agree, the quote to be present, and `citation_ids` to match
`source_spans`. A generated `[S99]` is just text unless the service resolves it
to authorized evidence.

This baseline emits one extractive claim. Free-form generation can contain
multiple atomic claims, each needing support. Split compound sentences before
scoring faithfulness. A citation at paragraph end should not be assumed to
support every clause.

### Deterministic extraction and abstention

The fallback scores each safe context sentence by non-stopword overlap with
the question. Transparent cue bonuses help temporal questions and the two
fixture forms about validation and endpoints. If the best score is below
`minimum_sentence_score`, the system returns:

```text
I do not have sufficient authorized evidence to answer.
```

The threshold is calibrated only for this tiny fixture. Raising it trades
answer rate for fewer unsupported answers; lowering it does the reverse.
Production calibration needs representative questions and explicit costs for
false answers versus abstentions.

The extractor proves lineage and safe failure, not natural language quality.
An LLM may synthesize a clearer response but adds model behavior, prompt
handling, decoding, and post-validation failure modes.

### Documents are untrusted

The adversarial fixture contains phrases asking the reader to ignore previous
instructions, expose a hidden prompt, and exfiltrate secrets. The system tags
all context entries `untrusted_document_content`. Configured indicators cause
the entire chunk to be excluded and recorded in `blocked_chunks`.

Pattern matching is deliberately limited. Attackers can translate, encode,
obfuscate, split, or indirectly express instructions. A production design
layers:

- source allowlisting, provenance, and trust classification;
- least-privilege retrieval and pre-model authorization;
- structured separation between instructions and document data;
- tool isolation and narrow egress;
- sensitive-data controls;
- output/citation validation;
- monitoring and adversarial regression sets;
- human approval for consequential actions.

Never claim that a pattern list solves prompt injection. The lab proves one
known attack fixture follows a fail-closed path.

### Tenant isolation

Lesson 42 filters chunks before scoring. Lesson 43 repeats the proof at the
consumer boundary: a Beta question explicitly asking for Alpha token policy
must contain no Alpha private document in candidates or context and must
abstain.

The tenant string in this local CLI is untrusted input. A real API must derive
tenant and document grants from verified identity and policy. The model is
never an authorization engine.

### Optional model endpoint

`openai_compatible_client.py` can send an already assembled safe context to a
local OpenAI-compatible `/chat/completions` endpoint. The reviewed config
allows only numeric IPv4 loopback (`127.0.0.1`), uses plain local HTTP, rejects
embedded URL credentials, and refuses to read or transmit an authorization
header or follow redirects. It labels documents with XML-like untrusted-data
boundaries and sets temperature zero.

That client records a raw model response. It does not make the response trusted.
Before accepting model output, parse claims, resolve citations, run
faithfulness checks, test abstention, and repeat the adversarial suite. The
optional path is not part of the repository’s verified CPU result.

## Prerequisites and preflight

Run:

```bash
cd lessons/phase-06-rag/43-grounded-generation-rag-evaluation-security
python3 --version
python3 -m json.tool configs/grounding.json >/dev/null
python3 -m json.tool data/questions.json >/dev/null
python3 -m json.tool data/forged-answer.json >/dev/null
```

Review the injection fixture as data. Do not execute or follow its statements:

```bash
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("data/adversarial-documents.jsonl").read_text())
print(d["document_id"], d["tenant_ids"], d["sections"][0]["section_id"])
PY
```

Lessons 41 and 42 need no pre-existing artifacts; the runner rebuilds them.

## Cost and safety

The required lab is offline, local CPU, and tiny. It creates no Kubernetes or
cloud resources.

Adversarial fixture text is inert source data. Keep it in controlled test
corpora so it is not mistaken for an instruction. Do not insert actual secrets
to test exfiltration; use canary strings or synthetic values.

The optional endpoint can expose retrieved text to another process. The
checked-in client restricts it to loopback. If you adapt it to a network
service, obtain data-transfer approval, authenticate both directions, encrypt
transport, minimize logged prompt content, set timeouts, restrict egress, and
verify retention. Never paste API keys into configs or shell history.

RAG cannot make unauthorized data safe after retrieval. Keep authorization
before scoring, reranking, context, model calls, logs, and caches.

## Predict before running

Write `artifacts/predictions.md`:

1. Can retrieval hit rate be perfect while answer accuracy is lower?
2. Which overlap sentence will be deduplicated in the token-policy context?
3. Why must the unsupported phone question abstain?
4. What authorized source might distract the cross-tenant token query?
5. Will citation syntax alone prove support?
6. Could a malicious chunk rank first?
7. What attacks will the literal pattern list miss?
8. Which metric would reveal a correct phrase backed by the wrong source?

Keep the prediction beside observed artifacts.

## Lab outline

1. Rebuild ingestion and retrieval prerequisites.
2. Run seven grounded questions.
3. inspect context ordering, budget, and overlap removal.
4. Trace one answer claim to source version and offsets.
5. Compare retrieval metrics with answer metrics.
6. Build an adversarial source snapshot and index.
7. test cross-tenant, injection, and citation-integrity paths.
8. Reject fail-open configuration and a forged citation.
9. Optionally record a local model response and evaluate it separately.

## Step-by-step lab

### 1. Run the complete verified path

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected final shape:

```text
retrieval hit=1.000 answer phrases=1.000 abstention=1.000
PASS: cross-tenant evidence absent, injection chunk blocked, and forged citation rejected
PASS: retrieval and answer metrics passed separately ...
```

Those exact quality values are assertions for this deterministic fixture. They
are not LLM or production RAG performance.

### 2. Inspect a claim-to-source trace

```bash
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("artifacts/example-answer.json").read_text())
print(r["answer"])
for claim in r["claims"]:
    print("claim:", claim["text"])
    for span in claim["source_spans"]:
        print(span)
PY
```

Compare the span with lesson 41’s normalized source:

```bash
rg -n "Tokens expire" \
  ../41-ingestion-chunks-embeddings-indexes/artifacts/index-a/documents.jsonl
```

### 3. Observe context budgeting and deduplication

```bash
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("artifacts/example-answer.json").read_text())
print(r["context_budget"])
for source in r["context"]:
    print(source["citation_id"], source["rank"], source["chunk_id"], source["text"])
PY
```

The overlapping token-expiry sentence should appear only once, even though two
source chunks contain it. Context may include irrelevant candidates; top-k
retrieval is not a sufficiency guarantee.

### 4. Compare component metrics

```bash
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("artifacts/grounding-results.json").read_text())
print("retrieval:", r["retrieval_metrics"])
print("answers:", r["answer_metrics"])
for case in r["cases"]:
    print(
        case["question_id"],
        "retrieval=", case["retrieval_hit"],
        "phrase=", case["expected_phrases_passed"],
        "abstain=", case["abstention_correct"],
    )
PY
```

If a future model fails, this table tells you whether to investigate retrieval,
assembly, or generation first.

### 5. Inspect the adversarial result

```bash
python3 -m json.tool artifacts/security-results.json
python3 src/grounding.py \
  --index artifacts/adversarial-index \
  --retrieval-config ../42-retrieval-hybrid-reranking/configs/retrieval.json \
  --grounding-config configs/grounding.json \
  answer \
  --question "What should the imported note ignore and exfiltrate?" \
  --tenant alpha >artifacts/adversarial-answer.json
python3 -m json.tool artifacts/adversarial-answer.json | sed -n '1,180p'
```

The imported note must appear under `blocked_chunks`, never `context`.

### 6. Optional local model

Start a reviewed local endpoint separately, then record the request input and
raw response:

```bash
python3 src/openai_compatible_client.py \
  --config configs/optional-model-endpoint.json \
  --grounded-request artifacts/example-answer.json \
  --output artifacts/model-response.json
```

This command fails if the configured host is not explicitly loopback. A raw
response is not accepted evidence until you add claim parsing and validation.

## Deliberate failure

Run:

```bash
./scripts/run-deliberate-failure.sh
sed -n '1,100p' artifacts/failures/unsafe-grounding.txt
sed -n '1,100p' artifacts/failures/forged-answer.txt
```

The first config asks to allow injection-marked chunks. Configuration validation
must stop before answering. The second answer cites nonexistent `S99` and a
missing chunk. Citation validation must stop. The third evaluation fixture is
tied to the wrong source hash and labels an Alpha-only chunk as relevant to
Beta; evaluation integrity checks must reject both confounds. The fourth
endpoint config embeds URL identity and targets a non-loopback address; the
optional client must reject it before opening a connection.

Expected:

```text
PASS: fail-open injection handling, forged citations, confounded questions, and unsafe model endpoints were rejected
```

Recovery requires restoring `block_chunk`, reviewing blocked content, and
regenerating claims only from citation labels provided to that request. Never
invent a source object to make an answer validator pass.

## Verification

Run:

```bash
python3 scripts/verify.py
python3 -m json.tool artifacts/results.json
```

The verifier requires perfect fixture retrieval hit, phrase, abstention, and
claim-support checks; no forbidden documents; a blocked adversarial document;
and a rejected forged citation. It also confirms every context entry is marked
untrusted.

## Troubleshooting

If an answerable fixture abstains, inspect retrieval candidates before lowering
the threshold. Then inspect context blocking/budget and sentence scores.
Changing a global threshold to repair one query may create unsupported answers
elsewhere.

If the cross-tenant query answers from a shared but irrelevant source, the
sufficiency threshold is too permissive for that confound. Add representative
negative questions and calibrate; do not grant access to the desired private
source.

If injection tests do not retrieve the malicious document, the defense was not
exercised. Confirm the adversarial index has 14 chunks and the question names
its terms. A test that passes only because the attack never reached the filter
is weak.

If citation validation fails after deduplication, map claims against the final
assembled context rather than pre-deduplicated candidates. Preserve source
offsets when extracting a substring.

If a model endpoint invents citation labels, reject or abstain. Prompt wording
alone is not enforcement.

## Evidence to collect

Keep:

- predictions and threshold rationale;
- prerequisite index manifest and retrieval config hashes;
- `grounding-results.json`, `security-results.json`, and `results.json`;
- one complete answer with context, claim, quote, and offsets;
- one supported retrieval miss or answer failure if you change the fixture;
- unsupported and cross-tenant abstention records;
- the blocked injection chunk and matched patterns;
- forged-citation failure;
- optional model endpoint identity, model revision, prompt, raw response,
  validator output, latency, and resource evidence if run.

## Exercises

1. Reduce context to 30 words and identify which answers lose evidence.
2. Reverse context order and measure answer changes.
3. Add a compound answer with two claims and require independent citations.
4. Create an obfuscated injection that bypasses literal patterns, then add a
   defense layer without claiming universal detection.
5. Add source trust tiers and require human review for low-trust evidence.
6. Replace whitespace budgeting with the deployed tokenizer.
7. Add an answer-sufficiency classifier trained only on synthetic data and
   document its limitations.
8. Connect a local model, parse citations, and run the same negative/security
   suite before comparing answer style.
9. Add a canary tool and prove retrieved text cannot trigger tool execution.

## Completion gate

You are finished when:

- retrieval and answer metrics are reported separately;
- every emitted claim maps to an authorized context label, chunk, source
  version, quote, and normalized offsets;
- overlapping sentences are deduplicated under an explicit budget;
- unsupported and cross-tenant questions abstain;
- no forbidden Alpha document appears for Beta;
- the injection document is retrieved for the test, blocked, and absent from
  context;
- forged citation text and fail-open configuration are rejected;
- you can explain why these tests reduce risk but do not prove RAG is free of
  hallucination or prompt injection.

## Cleanup

From this directory:

```bash
pwd
rm -rf artifacts/
```

When the phase is complete, remove prerequisite artifacts too:

```bash
rm -rf ../41-ingestion-chunks-embeddings-indexes/artifacts/
rm -rf ../42-retrieval-hybrid-reranking/artifacts/
```

Stop an optional model server and remove its caches according to your model and
data retention policy.

## Primary references

Reviewed 2026-10-21:

- [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401)
- [OWASP prompt-injection prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [Lost in the Middle: long-context position effects](https://aclanthology.org/2024.tacl-1.9/)
- [FActScore paper and repository](https://github.com/shmsw25/FActScore)
- [Kubernetes multi-tenancy guidance](https://kubernetes.io/docs/concepts/security/multi-tenancy/)

The original papers and official guidance describe threat and evaluation
models. Only this lab’s generated artifacts support statements about its
behavior.
