# Lesson 39 solution notes

The CPU artifact is intentionally marked `course-fixture` and
`deployable: false`. It validates packaging mechanics without pretending that
JSON contains adapter tensors. A real capstone must point the builder at the
PEFT directory from lesson 36; the builder then requires safetensors weights
and the verifier runs without `--allow-fixture`.

Changing adapter rank after packaging changes the file hash and must fail.
Rebuilding the manifest is legitimate only when the changed adapter is a new
release with training and evaluation evidence. It is not a repair for
unexplained mutation.

The strict capstone verifier requires a deployable package, the same frozen
evaluation contract for base and tuned artifacts, a passing tuned decision,
`oms-benchmark/v1` for both treatments, identical benchmark workloads, the same
engine/version/config and GPU model, and the base revision recorded by the
release. A throughput improvement cannot compensate for a failed safety gate,
and a quality improvement is not comparable if the workload changed.

Rollback means reapplying a previously stored immutable manifest and then
rerunning health, acceptance, and provenance checks. A mutable image tag or an
unrecorded adapter directory is not a rollback target.
