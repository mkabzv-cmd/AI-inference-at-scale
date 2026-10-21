# Lesson 18 report

## Environment and immutable inputs

- Repository commit:
- Workload hash:
- Optional vLLM image digest:
- Model revision:

## Predictions

Predict the late short request's TTFT and the page-fragmentation direction.

## Controlled results

| Experiment | Changed variable | Drain ticks or req/s | Short p95/TTFT | Peak KV pages |
|---|---|---:|---:|---:|

Simulation ticks are not milliseconds. Put real engine measurements in a
separate table.

## Timeline diagnosis

Explain admission, head-of-line blocking, page allocation, freeing, and any
preemption using specific timeline rows or engine metrics.

## Failure, repair, and limitations

Record the fairness failure, evidence, one-variable repair, correctness gate,
and what this experiment cannot establish.
