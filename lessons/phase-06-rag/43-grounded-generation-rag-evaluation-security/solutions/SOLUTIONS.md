# Lesson 43 solution notes

The verified generator is deterministic and extractive. It proves the plumbing
contract—authorized retrieval, bounded context, exact quotations, citations,
and abstention—without claiming neural answer quality.

Retrieval and answer metrics stay separate. A relevant chunk can appear in the
candidate list while the extractor chooses the wrong sentence. Conversely, a
generator may emit an expected phrase without retrieving the labeled evidence;
that is not a grounded success.

Retrieved documents are marked untrusted and scanned before context assembly.
Pattern matching is only one defense layer and will not detect every attack.
The strict fixture proves that a known malicious chunk is blocked and never
enters the context. Production systems also need source trust, isolation,
least-privilege tools, output validation, monitoring, and adversarial testing.

The forged answer fails because `S99` is not a supplied context label and its
quote is absent. Citation-shaped text is not evidence unless the service maps
it back to an authorized source span.
