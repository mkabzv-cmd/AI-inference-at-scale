# Troubleshooting Index

Published lessons should link symptoms to evidence rather than to random commands.

## Kubernetes

- Pod Pending: inspect requests, extended GPU resources, labels, taints,
  affinity, quotas, node capacity, and events.
- CrashLoopBackOff: inspect previous logs, command/args, configuration, mounted
  files, and exit status.
- Unready: inspect startup/readiness probes and model-load progress.
- Unreachable: inspect Service selectors, endpoints, ports, DNS, and network
  policy.

## GPU

- No `nvidia.com/gpu`: verify node driver/runtime and device plugin or DRA path.
- CUDA incompatibility: record host driver, container runtime, CUDA libraries,
  engine wheel, and architecture.
- OOM: separate model weights, runtime workspace, activations, and KV cache.

## Distributed

- Rank timeout: verify rendezvous address, ports, DNS, world size, and every rank.
- NCCL hang: compare rank logs, network reachability, interface selection, and
  collective ordering.
- Ray placement pending: inspect advertised resources, placement bundles,
  affinity, and total schedulable GPUs.

## Training

- Diverging loss: verify labels/masks, learning rate, precision, data quality,
  accumulation, and gradient norms.
- Resume mismatch: verify model, optimizer, scheduler, tokenizer, dataset, and
  world-size compatibility.
