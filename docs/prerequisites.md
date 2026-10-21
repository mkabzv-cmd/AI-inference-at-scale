# Prerequisites

## Required knowledge

- Basic Python: functions, modules, virtual environments, and stack traces.
- Basic shell usage: files, processes, pipes, environment variables, and SSH.
- Basic Git: clone, branch, commit, diff, and pull request.
- Conceptual awareness that transformers predict tokens. The course rebuilds the
  inference and training mental models.

## Required local software

- Git
- Python
- a container client compatible with OCI images
- `kubectl`
- AWS CLI for the AWS track
- Helm, introduced only after raw Kubernetes objects

Do not install every tool up front. Each published lesson should state and verify
its own exact requirements.

## Cloud requirements

The AWS path assumes:

- an EKS cluster;
- permission to inspect and scale a dedicated lab node group;
- one approximately 24 GB NVIDIA GPU for the single-GPU lane;
- up to three one-GPU nodes in one Availability Zone for distributed labs;
- a private model-artifact source or permission to download public artifacts.

The public repository must never contain the real account, role, cluster, subnet,
registry, or endpoint values.

## Recommended learner preflight

Before lesson 00, the learner should be able to:

```bash
python --version
git --version
kubectl version --client
aws --version
```

Cloud authentication and cluster access belong in a private local profile, never
in committed files.
