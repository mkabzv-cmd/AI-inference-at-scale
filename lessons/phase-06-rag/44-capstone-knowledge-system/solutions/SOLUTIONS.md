# Lesson 44 solution notes

The required CPU study uses four explicit system contracts. The “tuned”
variants are deterministic format proxies, not trained adapters; this is
recorded in every result. Their purpose is to validate that behavior adaptation
and knowledge retrieval are measured independently before optional real model
endpoints are substituted.

The RAG variants should answer all three current-knowledge questions with
citations. Base and tuned-without-retrieval proxies should abstain. The tuned
proxy should satisfy strict JSON behavior even though it lacks evidence. That
demonstrates why behavior and knowledge are complementary dimensions.

The update probe builds v1, v2, and v1 again. A successful proof has different
source hashes and answers for v1 versus v2, then an identical v1 answer and
manifest after rollback.

The Kubernetes service is private by construction: ClusterIP, no Ingress,
default-deny network policy, explicit labeled clients, non-root user,
read-only root filesystem, no service-account token, probes, and resource
bounds. The course principal header remains a demonstration adapter, not
production authentication.
