# Fixture runbook

Run `scripts/run-local-lab.sh`. It verifies the untouched passing fixture,
virtually applies each checked-in failing overlay, confirms the expected
violation code, proves operator-only mode rejects synthetic evidence, and
proves workspace initialization refuses to overwrite files.

No cluster, network endpoint, model, GPU, registry, or cloud resource is
created. There is no deployment or teardown command in this fixture.

If the passing fixture fails, read the first violation, recompute the actual
file hashes, and update the release bindings before rebuilding
`evidence-index.json`. Never weaken a verifier rule merely to make stale
evidence pass.
