# Lesson 47 solution notes

## Hash and provenance boundary

The provenance statement binds declared metadata to exact local bytes. It does
not prove that the source is trustworthy, the license conclusion is correct,
the content is safe, or a build was reproducible. Signatures and transparency
logs can bind an identity and build process; evaluation and policy address
different claims.

## Why safetensors is preferred

Formats that invoke general-purpose deserialization can execute or instantiate
unexpected objects. A data-only format reduces that attack surface, but parsing
libraries can still have vulnerabilities and tensor sizes can cause resource
exhaustion. Verify source, digest, format, size, and parser version.

## Network policy is not authentication

The policy limits which Pods can connect based on Kubernetes identity/labels.
It does not authenticate a human or authorize a tenant action. The restricted
service remains private until a platform-native gateway proves anonymous and
unauthorized denial.

## Deploy ordering

For restricted content, attach and verify the gate before making the content
available. Anonymous connection failure alone is not an identifiable auth
denial; test 401/403 from the intended gate, then test an authenticated but
unauthorized principal.
