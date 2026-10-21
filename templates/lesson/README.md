# NN — Lesson title

**Status:** outline | draft | review | published | refresh-needed
**Estimated time:**
**Compute profile:**
**Estimated GPU-minutes:**
**Estimated cloud cost:** state assumptions, not only a number
**Prerequisites:**
**Last validated:** YYYY-MM-DD
**Validated with:** tool, cluster, image, model, and hardware versions

## Why this matters

Connect the mechanism to a real inference, training, or operations problem.
Explain what goes wrong when the learner does not understand it.

## Learning outcomes

By the end, the learner can:

- explain the mechanism in plain language;
- execute the working baseline;
- inspect evidence from the relevant layers;
- diagnose the lesson's deliberate failure;
- change one variable and explain the result;
- remove every resource created by the lab.

## What you will build

Show the finished architecture with a Mermaid or ASCII diagram. State the
observable result, such as an HTTP response, scheduler placement, saved adapter,
or benchmark record.

## Files in this lesson

List every runnable file and explain its purpose. A learner should never have to
guess which manifest, script, or source file a command uses.

## Concepts and mental model

Teach from the learner's current level. Define new vocabulary, distinguish
similar concepts, use a concrete analogy where it helps, and state where the
analogy stops being accurate.

## Under the hood

Trace the execution path hidden by the high-level command or API. Include
object ownership, tensor shapes, memory arithmetic, scheduling decisions,
network hops, process/rank behavior, or loss computation as appropriate.

## Prerequisites and preflight

Provide exact commands that verify:

- required local tools and versions;
- the active Kubernetes and cloud contexts;
- permissions and cluster capabilities;
- available CPU, memory, disk, and GPU resources;
- lesson-specific environment variables.

Preflight must fail before creating expensive resources when a requirement is
missing.

## Cost and safety

State what can incur cost, the expected duration, how to avoid accidental public
exposure, and the stop conditions. Use a lesson-specific namespace and default
to `ClusterIP`.

## Predict before running

Ask the learner to write down predictions about the mechanism and expected
state. Refer back to these predictions after the experiment.

## Lab outline

Summarize the experiment before the detailed walkthrough:

1. Establish a correct baseline.
2. Inspect the mechanism.
3. Change one controlled variable.
4. Introduce and diagnose one failure.
5. Repair, verify, and clean up.

## Step-by-step lab

For every step:

1. explain the purpose;
2. give a copyable command from an explicit working directory;
3. show abbreviated expected output or state;
4. explain what the output proves;
5. include a diagnostic branch for likely failures.

All referenced source, container, manifest, chart, configuration, query, and
script files must exist in the lesson directory.

## Inspect what happened

Use logs, events, metrics, ownership, endpoints, process information, GPU
telemetry, traces, or profiler output to connect the result to the internals.

## Deliberate failure

Break one thing at a time. Ask for a prediction, show how to collect evidence,
provide a diagnosis tree, and require the learner to repair the system.

## Controlled experiment

Change exactly one important variable. Record correctness, performance, memory,
resource placement, or communication evidence before and after the change.

## Verification

Provide an automated or unambiguous behavioral check. “The Pod is Running” is
not enough when the lesson promises a working API.

## Expected result

Show the important output fields while making clear which generated values,
times, names, addresses, or hashes will differ.

## Troubleshooting

Organize symptoms by layer. Include commands that distinguish configuration,
scheduling, image, storage, process, model, network, and application failures.

## Evidence to collect

- `results.json`
- `report.md`
- relevant logs, events, diagrams, benchmark output, or profiler evidence

Evidence paths containing account or cluster details must remain ignored until
sanitized.

## Knowledge check

Ask questions that require explaining why, predicting behavior, or choosing
diagnostic evidence—not only recalling commands.

## Exercises

Include at least one guided exercise and one independent challenge. Put
solutions in a clearly labelled collapsible section or `solutions/` directory.

## Completion gate

Define observable acceptance criteria covering understanding, successful
execution, failure diagnosis, verification, saved evidence, and cleanup.

## Cleanup

Provide:

1. the exact deletion commands;
2. commands that prove namespaced and cluster-scoped resources are gone;
3. cloud-capacity scale-down steps where applicable;
4. checks for leftover load balancers, volumes, snapshots, images, and model
   caches where applicable.

## Primary references

Prefer official documentation and original papers. Record pinned links and a
last-validated date. Clearly separate required reading from optional depth.
