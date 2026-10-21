# Threat model: open-model platform

## Scope and assumptions

Name users, callers, environments, data classifications, public/private
boundaries, model capabilities, excluded systems, and review date.

## Assets

- Base weights and tokenizer
- Training/evaluation datasets
- Adapters and checkpoints
- Retrieval sources, chunks, embeddings, and indexes
- Container images and dependencies
- Prompts, responses, logs, traces, and metrics
- Cloud credentials, workload identities, and authorization policy
- GPU/CPU/storage/network capacity

## Trust boundaries and data flows

Draw identities and data entering ingestion, training, registry, deployment,
gateway, retrieval, model serving, telemetry, and operators.

## Threat register

| ID | Asset/flow | Threat | Preconditions | Impact | Existing control | Verification | Residual risk | Owner |
|---|---|---|---|---|---|---|---|---|

Include supply-chain substitution, unsafe deserialization, prompt injection,
cross-tenant retrieval, data poisoning, model extraction, denial of service,
credential theft, public exposure, log leakage, and incomplete deletion.

## Release gates

Define anonymous denial, authorization, provenance, policy admission,
evaluation, vulnerability/license review, rollback, incident response, and
cleanup evidence.
