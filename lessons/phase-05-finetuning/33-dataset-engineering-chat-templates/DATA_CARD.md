# Data card: oms-operations-mini

## Purpose

This is a tiny, synthetic teaching dataset for tracing a chat example through
normalization, templating, token IDs, assistant-only labels, deterministic
splits, fingerprints, and packing arithmetic. It is too small to claim useful
model adaptation.

## Creation and ownership

All examples were authored for this course and released under CC0-1.0. They do
not contain customer data, production logs, account identifiers, credentials,
or copied support conversations.

## Intended use

- CPU-safe dataset pipeline exercises.
- Training-loop smoke tests in later lessons.
- Demonstrating provenance, split, mask, and leakage checks.

## Out-of-scope use

- Production operations advice.
- Kubernetes or AWS factual evaluation.
- Safety evaluation.
- Claims that a fine-tuned model generalizes.

## Structure

Each JSONL row contains a stable ID, source label, license, and exactly three
messages in system/user/assistant order. The educational preprocessing path
uses UTF-8 bytes as token IDs so masking can be inspected without downloading a
tokenizer. Actual model training must re-render with the exact target model's
versioned tokenizer and chat template.

## Known limitations

The corpus is tiny, stylistically uniform, single-turn, English-only, and
course-authored. Hash-based splits are mechanically independent but not
statistically representative. Exact hashes do not detect paraphrased leakage.
