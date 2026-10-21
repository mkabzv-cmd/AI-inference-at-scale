# 33 — Dataset engineering and chat templates

**Status:** draft
**Time:** 5–7 hours
**Compute:** `local-cpu`
**GPU budget:** none
**Prerequisites:** 32
**Last reviewed:** 2026-10-21

## Why this matters

Fine-tuning does not begin with `trainer.train()`. It begins with a data
contract. A training job can complete perfectly while teaching the wrong role
boundaries, leaking evaluation answers into training, optimizing tokens that
should be masked, silently truncating responses, or consuming text whose
license and provenance are unknown.

Chat models do not receive a Python list of message dictionaries. A chat
template serializes roles and content into text or token IDs. The tokenizer then
turns that representation into IDs. A collator creates labels, padding,
attention boundaries, and perhaps packed sequences. The loss sees only those
labels. One wrong template or mask can therefore change the actual learning
task while the high-level dataset still looks correct.

This lesson builds the whole transformation with standard-library Python:

```text
source JSONL
  -> schema and license checks
  -> Unicode/whitespace normalization
  -> exact-content fingerprint
  -> stable deterministic split
  -> chat serialization
  -> educational byte token IDs
  -> assistant-only loss labels
  -> manifest and file hashes
  -> split/mask audit
  -> padding-versus-packing report
```

The checked-in corpus is synthetic and deliberately tiny. It exists to teach
mechanics and to support later smoke tests, not to produce a useful operations
assistant. Because the required path uses UTF-8 bytes as educational token IDs,
you can inspect every boundary without downloading a model. Before real
training, you must repeat the pipeline with the exact target model's pinned
tokenizer and official chat template.

## Learning outcomes

By the end, you can:

- define a stable JSONL record contract for supervised chat examples;
- separate source data, normalized data, rendered conversations, token IDs,
  labels, and packed batches;
- explain why a chat template is part of the model interface;
- identify which tokens receive loss in assistant-only supervised fine-tuning;
- explain the conventional `-100` ignore label without confusing it with a
  tokenizer ID;
- make train, validation, and test membership deterministic without depending
  on input order;
- fingerprint source and generated files for reproducibility;
- reject disallowed licenses and exact duplicate content before training;
- distinguish exact duplicate detection from semantic leakage detection;
- calculate padding waste and explain when packing changes attention semantics;
- write a data card that states origin, purpose, limitations, and prohibited
  interpretations.

## What you will build

You will convert 12 synthetic Kubernetes-operations conversations into three
processed splits. Each processed row includes:

- normalized messages;
- a split name;
- a SHA-256 content fingerprint;
- rendered chat text;
- educational byte-level `input_ids`;
- assistant-only `labels`;
- total and supervised token counts.

The build creates `manifest.json` with input/config hashes, per-split hashes and
counts, source/license counts, normalization behavior, and an explicit warning
that the educational tokenizer must be replaced for real model training.

You will also create `packing-report.json`, which compares padding every example
to a fixed maximum with a simple greedy bin pack. Finally, you will run a broken
fixture that contains unapproved provenance and duplicated content, and prove
that the pipeline rejects it.

## Files in this lesson

```text
33-dataset-engineering-chat-templates/
├── README.md
├── DATA_CARD.md
├── configs/
│   └── dataset.json
├── data/
│   ├── broken/
│   │   └── duplicate-and-license.jsonl
│   └── raw/
│       └── examples.jsonl
├── schemas/
│   └── example.schema.json
├── scripts/
│   ├── run-cpu-lab.sh
│   └── run-deliberate-failure.sh
├── solutions/
│   └── SOLUTIONS.md
└── src/
    ├── audit_dataset.py
    ├── build_dataset.py
    └── packing_report.py
```

Generated splits and reports are written beneath ignored `artifacts/`. The raw
teaching examples and data card are intentionally tracked.

## Under the hood

### Normalization is a modeling decision

The builder applies Unicode NFKC normalization and collapses whitespace inside
each message. This makes exact hashing resistant to harmless spacing and some
equivalent Unicode representations. It can also erase meaningful formatting.
For code, tables, poetry, or whitespace-sensitive tasks, the course policy
would be wrong. A production pipeline must version the normalization function
and test it against representative data.

Normalization happens before content hashing. As a result, two rows that differ
only by collapsed whitespace become exact duplicates. IDs are checked
separately so neither repeated IDs nor repeated content are accepted.

### Stable splitting

A naïve `shuffle(seed); slice(...)` changes many existing assignments when
examples are inserted or removed. This lesson hashes:

```text
SHA-256(split seed + ":" + stable example ID)
```

The first 64 bits map to a value in `[0, 1)`, which is compared with checked-in
thresholds. Existing IDs keep their split when unrelated rows are appended.
Changing the seed or an ID changes membership and therefore creates a new
evaluation contract.

Small datasets can still produce an empty split by chance. The builder fails
rather than silently continuing. The checked-in seed was selected to produce
non-empty train, validation, and test splits for this teaching corpus; it is
not evidence of statistical representativeness.

### Rendering and labels

For each message, the builder appends a role prefix, content, and suffix. UTF-8
bytes become educational token IDs from 0 to 255. Labels have the same length:

```text
system prefix/content     -> -100
user prefix/content       -> -100
assistant role prefix     -> -100
assistant response bytes  -> matching input byte ID
assistant newline         -> matching input byte ID
conversation end marker   -> -100
```

Many PyTorch cross-entropy paths use `-100` as an ignore index, meaning those
positions do not contribute directly to the loss. `-100` is not a vocabulary
token. The model still reads masked prompt tokens as context; they simply do not
have target loss terms in this objective.

Real tokenizers may split role markers, newlines, Unicode, and whitespace
differently. Some official model templates add generation prompts or special
tokens through tokenizer APIs. Never hand-recreate a production template from
memory. Pin the tokenizer revision, render a golden example, and assert exact
IDs and mask boundaries.

### Fingerprints and manifests

The content fingerprint hashes canonical normalized messages. The file
fingerprints hash exact generated bytes. They answer different questions:

- content hash: "Is this conversation duplicated?"
- file hash: "Are these exact processed split bytes unchanged?"

The manifest also records the input and configuration hash. Its `input_path`
field is only the source filename, not an absolute checkout path, so identical
source/config bytes produce a portable manifest across directories. The hash,
not that display name, identifies the input. A reproducible training run should
reference the immutable manifest, not only a friendly dataset name.

### Leakage is broader than duplication

Exact hashes catch copied rows. They do not catch paraphrases, common templates,
near-duplicate incidents, answers derived from the same source document, the
same customer across splits, future information in a temporal benchmark, or
test questions embedded in instructions. Those require domain-aware grouping,
similarity search, source-family isolation, temporal cutoffs, and human review.

Treat "no exact duplicates" as one audit result, never as proof of no leakage.

### Padding and packing

Padding each example to a fixed length wastes slots but keeps boundaries simple.
Packing several examples into one fixed-length sequence raises utilization.
Unless the collator resets positions and/or applies block-diagonal attention,
later examples may attend to earlier examples. End markers alone do not
mathematically prevent cross-example attention.

The supplied packing script reports storage utilization only. It does not
declare the packed layout safe for a particular trainer.

## Prerequisites and preflight

Run from this lesson directory:

```bash
cd lessons/phase-05-finetuning/33-dataset-engineering-chat-templates
python3 --version
test -f data/raw/examples.jsonl
test -f configs/dataset.json
python3 -m json.tool configs/dataset.json >/dev/null
```

Confirm that source rows are one JSON object per line:

```bash
wc -l data/raw/examples.jsonl
python3 - <<'PY'
import json
from pathlib import Path

for number, line in enumerate(
    Path("data/raw/examples.jsonl").read_text().splitlines(),
    start=1,
):
    json.loads(line)
print("all source rows parse")
PY
```

Read `DATA_CARD.md` and verify that every source/license statement is compatible
with your intended use. Do not replace this corpus with private tickets, chats,
logs, documents, or customer prompts unless you have an approved governance and
redaction process.

## Cost and safety

The lesson uses local CPU only and makes no network request. The checked-in data
is synthetic.

Real datasets can expose personal data, credentials, internal identifiers,
copyrighted text, security incidents, or contractual restrictions. Hashing does
not anonymize content; a hash is a stable identifier and may itself be
sensitive when linked to another system. Do not commit generated splits from
private source data. Use approved storage, access control, retention, deletion,
and review processes.

Training on a sample grants the model no authority to perform the action it
describes. The examples teach response style, not permissions.

## Predict before running

Create `artifacts/predictions.md` and answer:

1. Which message bytes should receive loss?
2. Does masking the user content prevent the model from reading it?
3. If input row order is reversed, should stable ID-based split membership
   change?
4. Will an exact duplicate with a new ID be caught?
5. Will a paraphrase be caught by the current exact hash?
6. Which should have higher slot utilization: padding every example to 1024 or
   greedily packing examples?
7. Does higher packing utilization prove an equivalent training objective?
8. Which failure should appear first for the broken fixture: license rejection
   or duplicate rejection? Why can validation order affect the reported error?

Keep the predictions; add observed results rather than rewriting them.

## Lab outline

1. Inspect the data contract, source rows, and data card.
2. Trace one conversation through normalization and rendering.
3. Build deterministic splits and the manifest.
4. Audit hashes, membership, lengths, and assistant-only masks.
5. Compare padding and packing arithmetic.
6. Prove ordering independence.
7. Run a deliberate provenance/duplication failure.
8. Design a near-duplicate audit appropriate to a real domain.

## Step-by-step lab

### 1. Inspect one raw example

```bash
sed -n '1p' data/raw/examples.jsonl | python3 -m json.tool
```

Identify the stable ID, source, license, role sequence, and intended assistant
target. Inspect the template configuration:

```bash
python3 -m json.tool configs/dataset.json
```

The template is course-specific. It is not claimed to be Qwen, Llama, Mistral,
or another model's official template.

### 2. Run the complete pipeline

```bash
chmod +x scripts/*.sh
./scripts/run-cpu-lab.sh
```

Expected final output shape:

```text
PASS: 12 unique examples; deterministic splits, hashes, and assistant-only masks verified
pad utilization=<fraction>; pack utilization=<larger fraction>
Evidence written under .../artifacts
```

Generated split counts are data-dependent. Inspect the manifest:

```bash
python3 -m json.tool artifacts/dataset/manifest.json
```

Then verify each recorded split hash directly:

```bash
python3 src/audit_dataset.py --dataset-dir artifacts/dataset
```

### 3. Trace the mask boundary

```bash
python3 - <<'PY'
import json
from pathlib import Path

row = json.loads(
    Path("artifacts/dataset/train.jsonl").read_text().splitlines()[0]
)
first = next(i for i, label in enumerate(row["labels"]) if label != -100)
rendered = row["rendered_text"].encode("utf-8")
print("id", row["id"])
print("first supervised byte", first)
print("context before boundary", rendered[max(0, first - 40):first])
print("supervised prefix", rendered[first:first + 60])
print("supervised bytes", row["supervised_token_count"])
PY
```

The first supervised byte should be assistant response content, after the fixed
assistant role marker. Confirm that `input_ids` and `labels` have identical
length.

### 4. Prove order-independent membership

Create a reversed copy under ignored artifacts:

```bash
tail -r data/raw/examples.jsonl > artifacts/reversed.jsonl
python3 src/build_dataset.py \
  --input artifacts/reversed.jsonl \
  --config configs/dataset.json \
  --output-dir artifacts/reversed-dataset
```

On systems without `tail -r`, use:

```bash
python3 - <<'PY'
from pathlib import Path

source = Path("data/raw/examples.jsonl").read_text().splitlines()
Path("artifacts/reversed.jsonl").write_text(
    "\n".join(reversed(source)) + "\n"
)
PY
```

Compare ID-to-split mappings:

```bash
python3 - <<'PY'
import json
from pathlib import Path

def mapping(root):
    result = {}
    for split in ("train", "validation", "test"):
        for line in (root / f"{split}.jsonl").read_text().splitlines():
            row = json.loads(line)
            result[row["id"]] = split
    return result

first = mapping(Path("artifacts/dataset"))
second = mapping(Path("artifacts/reversed-dataset"))
assert first == second, (first, second)
print("PASS: membership is independent of input order")
PY
```

File hashes may differ because row order inside a split follows input order.
Membership stability and byte-for-byte file stability are different contracts.
If exact output bytes must also be order-independent, sort rows by stable ID
before writing and version that behavior.

### 5. Interpret packing

```bash
python3 -m json.tool artifacts/packing-report.json
```

Calculate the wasted slots yourself:

```text
padding waste = examples × max_length - sum(example lengths)
packing waste = packed sequences × max_length - sum(example lengths)
```

Explain why a trainer must still handle example boundaries even if packing uses
all slots.

## Deliberate failure

Run the checked-in broken fixture:

```bash
./scripts/run-deliberate-failure.sh
sed -n '1,80p' artifacts/expected-failure.txt
```

It should be rejected. The first row has a license not present in the allowlist,
and the two rows also normalize to identical message content. The builder
validates licenses while canonicalizing, so it may stop before reaching the
duplicate audit. This is an important validation property: one reported failure
does not prove that no additional failures exist.

To expose the duplicate next, copy the fixture under artifacts and change only
`Unknown` to `CC0-1.0`, then rerun the builder:

```bash
sed 's/"Unknown"/"CC0-1.0"/' \
  data/broken/duplicate-and-license.jsonl \
  > artifacts/duplicate-only.jsonl

python3 src/build_dataset.py \
  --input artifacts/duplicate-only.jsonl \
  --config configs/dataset.json \
  --output-dir artifacts/should-not-exist
```

This command must exit nonzero and identify duplicate content hashes. Recovery
means fixing or intentionally adjudicating the source records—not weakening the
allowlist or deleting duplicate checks.

## Verification

Run:

```bash
python3 src/audit_dataset.py --dataset-dir artifacts/dataset
./scripts/run-deliberate-failure.sh
python3 -m json.tool artifacts/packing-report.json >/dev/null
```

Also ensure the test split contains no training content hash:

```bash
python3 - <<'PY'
import json
from pathlib import Path

def hashes(name):
    path = Path("artifacts/dataset") / f"{name}.jsonl"
    return {
        json.loads(line)["content_sha256"]
        for line in path.read_text().splitlines()
    }

train = hashes("train")
validation = hashes("validation")
test = hashes("test")
assert train.isdisjoint(validation)
assert train.isdisjoint(test)
assert validation.isdisjoint(test)
print("PASS: exact normalized content is disjoint")
PY
```

Verification proves the declared mechanical contract for this dataset. It does
not prove factual quality, representative sampling, absence of paraphrased
leakage, legal sufficiency, or model usefulness.

## Troubleshooting

If the builder reports an empty split after you add or remove many examples,
inspect the deterministic hash distribution. Do not move a single inconvenient
example into test by hand. Review the seed or thresholds as a versioned dataset
change.

If a license is rejected, verify the source and approved use. Do not simply add
the string to the allowlist. The allowlist represents a governance decision,
not a spelling dictionary.

If `no supervised tokens remain`, inspect role order, empty assistant content,
and the masking policy. Training all labels as `-100` yields no learning signal.

If real model training produces bizarre role-marker output, compare the exact
tokenizer revision and its `apply_chat_template` output against a golden
example. Avoid adding special tokens twice.

If packing looks impossibly efficient, inspect whether any example exceeded the
maximum and whether the algorithm silently truncated it. The supplied script
fails on overlength examples instead of truncating.

If `tail -r` is unavailable, use the Python reversal snippet. Platform-specific
shell behavior should not alter the dataset contract.

## Evidence to collect

Retain locally:

```text
artifacts/
├── predictions.md
├── dataset/
│   ├── manifest.json
│   ├── train.jsonl
│   ├── validation.jsonl
│   └── test.jsonl
├── packing-report.json
├── reversed.jsonl
├── reversed-dataset/
├── duplicate-only.jsonl
├── expected-failure.txt
└── report.md
```

In `report.md`, record:

- the intended task and out-of-scope uses;
- source and license policy;
- normalization version and consequences;
- split algorithm and seed;
- exact versus semantic leakage boundary;
- rendered golden conversation and first supervised position;
- token-length and supervised-token counts by split;
- padding and packing utilization;
- model tokenizer/template changes required before lesson 35;
- unresolved data risks.

Do not publish generated private data merely because the artifact directory is
ignored.

## Exercises

1. Add a malformed role-order fixture and a test that rejects it.
2. Sort each split by ID before writing and show that reversed input now creates
   identical split file hashes.
3. Add a `group_id` and make related examples share a split.
4. Implement word or character n-gram Jaccard similarity to flag likely
   paraphrases. Calibrate a review threshold rather than automatically deleting
   everything above it.
5. Add a temporal cutoff field and prove that future examples cannot enter
   training for a time-based test.
6. Load a pinned Hugging Face tokenizer in a separate environment, render one
   example with its official chat template, and save the tokenizer revision and
   golden IDs.
7. Compare assistant-only loss with loss on the full conversation. Explain what
   behavior each objective encourages.
8. Design block-diagonal attention metadata for two packed examples.
9. Add personally identifiable information detection to a private-data
   pipeline, then explain why automated detection is not complete governance.
10. Extend the data card with annotator instructions, known disagreements, and
    deletion procedures.

## Completion gate

You are done when:

- the normal build and audit pass;
- the broken provenance fixture fails;
- the duplicate-only fixture fails for duplication;
- ID-to-split membership survives reversed input;
- you can point to the first supervised byte and explain every preceding mask;
- the manifest hashes the source, config, and generated splits;
- your report distinguishes exact duplication from broader leakage;
- you have identified the exact target tokenizer/template work required before
  real training;
- the data card makes no claim that the tiny synthetic corpus is useful
  training data.

## Cleanup

Remove only generated lesson artifacts:

```bash
rm -rf -- artifacts
test ! -e artifacts
```

Do not delete checked-in `data/raw/` or `DATA_CARD.md`. For a private extension,
follow the source system's approved retention and deletion process; deleting a
local processed copy may not remove upstream exports, object-store versions,
indexes, caches, or training checkpoints.

This lesson creates no Kubernetes or AWS resources.

## Primary references

Sources were reviewed on 2026-10-21:

- [Hugging Face Transformers chat templates](https://huggingface.co/docs/transformers/main/en/chat_templating)
- [Hugging Face Datasets dataset card guidance](https://huggingface.co/docs/hub/en/datasets-cards)
- [Dataset Cards for Dataset Documentation](https://arxiv.org/abs/2103.11410)
- [Data Statements for Natural Language Processing](https://aclanthology.org/Q18-1041/)
- [PyTorch cross-entropy loss and ignore index](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

The standard-library build and audit are author-validated. Integration with a
specific model tokenizer remains a later lesson task and must pin the model and
tokenizer revisions.
