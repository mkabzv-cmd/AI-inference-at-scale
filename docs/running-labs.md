# Running the Labs

This course is meant to be executed, not only read. A published lesson contains
the explanation and the files needed to reproduce its result.

## Current validation boundary

Lessons 00–10 are practical drafts, not published lessons. Automated checks
confirm repository structure, metadata consistency, source syntax, relative
links, and common secret patterns. They do not prove that your container
runtime, local cluster, EKS cluster, GPU driver, IAM permissions, model access,
or regional AWS configuration matches the lesson.

Treat expected output as a target to verify, not as proof that the command was
already executed in your environment. A lesson becomes `published` only after
its applicable paths are run from clean environments and independently
reviewed.

## What “runnable” means

A completed practical lesson must provide:

- the exact directory from which each command runs;
- source code, container files, Kubernetes manifests, Helm charts, or scripts
  used by the lab;
- a preflight that fails early when a required tool or cluster capability is
  missing;
- commands to build, deploy, inspect, test, deliberately break, repair, and
  remove the workload;
- short examples of the output or state the learner should expect;
- verification that checks behavior rather than merely checking that a command
  exited successfully;
- a cleanup command plus a second command that proves cleanup finished.

Cloud identifiers, image repositories, model IDs, and versions that vary by
learner are passed through environment variables. Lessons must not require
editing committed files to insert an AWS account ID, cluster endpoint, token,
or credential.

## Read before copying commands

Shell blocks use these conventions:

```bash
# A comment explains intent or tells you what must be changed.
command --flag value
```

Text such as `<YOUR_VALUE>` is a placeholder, not text to paste literally.
Prefer exporting the value once:

```bash
export LAB_NAMESPACE="oms-lesson-05"
export AWS_REGION="eu-west-1"
```

Then inspect it before a cloud command:

```bash
printf 'namespace=%s region=%s\n' "$LAB_NAMESPACE" "$AWS_REGION"
```

Do not put secrets in environment examples that might be committed to shell
history. Authentication belongs in the AWS CLI, container-registry, or model
provider's supported credential store.

## Command prompts and output

Commands are shown without a `$` prompt so an entire block can be copied. A
separate `text` block represents abbreviated output:

```bash
kubectl get pods -n "$LAB_NAMESPACE"
```

```text
NAME                         READY   STATUS    RESTARTS   AGE
example-6d4f...              1/1     Running   0          20s
```

Generated names, ages, IP addresses, hashes, and timings will differ. Compare
the meaningful fields, such as `READY`, `STATUS`, requested GPU count, HTTP
status, or response schema.

## Two execution tracks

### Local CPU track

The early Kubernetes mechanics use a disposable local cluster. This keeps
reconciliation, networking, probes, and Helm experiments free and fast.

The lesson tells you which supported local-cluster tool it was validated with.
Do not point a cleanup command at a shared or production cluster.

Before applying anything, verify the active context:

```bash
kubectl config current-context
kubectl cluster-info
```

### AWS GPU track

GPU labs use an existing EKS cluster and a dedicated lab GPU node group. They
must:

1. print the active AWS identity, region, cluster, and Kubernetes context;
2. verify that the target node group is a lab resource;
3. show estimated GPU-minutes before scaling it up;
4. deploy into a lesson-specific namespace;
5. use a `ClusterIP` Service unless a later security lesson explicitly teaches
   external exposure;
6. remove the workload and return optional GPU capacity to its starting size.

Never run a scale command until you have read it and confirmed the cluster and
node-group variables.

## The lab loop

Every practical lesson follows the same sequence.

### 1. Predict

Write down what you expect to happen and why. Examples:

- Which controller will recreate a deleted Pod?
- Will a readiness failure restart the container?
- Why will this GPU Pod remain Pending?
- Which layer owns the model cache?

### 2. Preflight

Check tools, context, permissions, architecture, available resources, and free
disk space. Preflight is evidence that the experiment started from a known
state.

### 3. Establish the baseline

Run the simplest correct version. Save the commands and observations requested
by the lesson.

### 4. Inspect the mechanism

Use status, events, logs, ownership, endpoints, process information, or GPU
telemetry to follow what the system actually did.

### 5. Break one thing deliberately

Change one variable and predict the failure. The exercise is complete only when
you can identify the failing layer from evidence.

### 6. Repair and verify

Restore the system and run a behavioral check, such as an HTTP request with an
expected response or a scheduler placement assertion.

### 7. Clean up and prove it

Deletion is not enough. Check that lesson namespaces, Pods, Jobs, Services,
volumes, load balancers, and optional GPU nodes are gone or back at their
starting state.

## Evidence directory

Lessons may ask you to save local evidence under an ignored `artifacts/`
directory:

```text
artifacts/
├── commands.log
├── events.txt
├── expected-vs-observed.md
├── results.json
└── report.md
```

Review files before sharing them. Kubernetes output can contain internal IP
addresses, registry locations, cluster names, IAM role names, and other details
that do not belong in a public issue or pull request.

## When a command fails

Do not immediately paste a replacement command from the internet. Record:

1. the exact command;
2. the complete error;
3. the current context and namespace;
4. relevant object status and recent events;
5. the layer you believe failed.

Then use the lesson's troubleshooting tree. A failed lab that is explained from
evidence is often more valuable than a clean first run.

## Safety stop conditions

Stop the lab and investigate before continuing if:

- the Kubernetes context is not the intended lab cluster;
- a command would modify a shared namespace;
- a manifest creates a public load balancer unexpectedly;
- a GPU node group scales beyond the lesson's declared maximum;
- a model license or access requirement is unclear;
- a command prints credentials or other secret material;
- cleanup leaves chargeable cloud resources you cannot identify.
