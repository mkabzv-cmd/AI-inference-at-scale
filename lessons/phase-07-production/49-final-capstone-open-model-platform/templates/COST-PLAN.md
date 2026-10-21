# Cost and capacity plan

## Budget boundary

- Currency and hard experiment limit: __REQUIRED__
- GPU-hours and wall-clock limit: __REQUIRED__
- Approved instance/node choices and quotas: __REQUIRED__
- Owner who can stop the run: __REQUIRED__

## Estimate inputs

Record price source and retrieval time, nodes, GPUs per node, expected
utilization window, storage, data transfer, load balancers, logs/metrics, image
and model storage, backups, and safety margin: __REQUIRED__

## Stop conditions

State the automated and manual stop conditions for elapsed time, spend, error
rate, queue growth, failed readiness, missing telemetry, and unintended public
exposure: __REQUIRED__

## Actuals and variance

Record observed GPU-hours, wall time, billed/estimated amount, source, variance,
and explanation. Do not label an estimate as billed cost: __REQUIRED__

## Post-teardown retention

List intentionally retained artifacts and their ongoing storage/logging cost.
Everything else must appear in the cleanup after-inventory: __REQUIRED__
