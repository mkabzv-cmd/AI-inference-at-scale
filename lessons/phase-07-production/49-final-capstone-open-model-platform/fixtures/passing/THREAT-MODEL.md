# Fixture threat model

The protected asset is verifier integrity. The fixture contains no private
model, corpus, prompt, account identifier, credential, endpoint, or measured
result.

Threats exercised are missing gate evidence, model-revision substitution,
public Kubernetes exposure, unverified cleanup, mutable or mismatched bytes,
unresolved markers, and a synthetic fixture being presented as a live release.

Controls are exact hashes, cross-document IDs, a private manifest scanner,
origin/attestation rules, an exact file allowlist, checked failure overlays, and
the mandatory `--require-operator-run` completion invocation.

Residual risk: the verifier cannot prove that an operator's claim is truthful
or that an external system enforced a policy. Protected CI, provenance,
independent review, and live negative tests remain necessary.
