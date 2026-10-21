# ADR: engine for the stated open-model workload

**Status:** proposed
**Date:** replace
**Decision owners:** replace

## Context and SLO

State users, request shape, prompt/output distributions, concurrency, quality
gate, latency objective, throughput objective, hardware and cost ceiling.

## Controlled evidence

Link the sanitized raw `oms-benchmark/v1` files, environment fingerprint,
engine configs, immutable image/model identifiers, repetitions and uncertainty.

## Options considered

### Transformers reference server

State evidence, strengths, weaknesses and operational implications.

### vLLM

State evidence, strengths, weaknesses and operational implications.

### SGLang

State evidence, strengths, weaknesses and operational implications.

### llama.cpp

Separate runtime effects from GGUF quantization/artifact effects.

## Decision matrix

Copy the precommitted weights and add 1–5 scores with one evidence sentence per
score. A numerical total without evidence is not a decision.

## Decision

Name the selected engine for this workload—not “the best engine.”

## Consequences

List accepted trade-offs, migration cost, unsupported features, monitoring,
capacity assumptions and security work still required.

## Revisit triggers

Examples: model family changes, context length changes, GPU changes, new engine
release, quality regression, SLO change or measured traffic distribution change.
