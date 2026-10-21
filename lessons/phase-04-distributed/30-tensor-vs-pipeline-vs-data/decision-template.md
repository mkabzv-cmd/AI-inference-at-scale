# Parallel strategy decision

## Frozen inputs

- model ID and revision:
- image digest and reported versions:
- node instance type and node identities:
- request SHA-256:
- request count/concurrency:
- context/token limits:

## Correctness

Describe the behavioral gate for DP, TP, and PP.

## Evidence table

| strategy | fits model? | median E2E | p90 E2E | requests/s | GPU memory | communication evidence | failure effect |
|---|---|---:|---:|---:|---:|---|---|
| DP | | | | | | | |
| TP | | | | | | | |
| PP | | | | | | | |

## Recommendation

Tie the choice to model fit and workload. State what would change the decision.

## Limitations

List sample size, measurement omissions, network/hardware scope, and anything
that prevented a comparable run.
