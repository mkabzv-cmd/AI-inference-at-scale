# Lesson 45 solution notes

## First bottleneck in the simulator

The fake service admits two requests to its model slots. Above that, requests
wait on a semaphore. Queue time therefore rises before computation time per
admitted request changes. TTFT includes queue plus simulated prefill, so p95
TTFT is the first configured SLO to breach.

## Why throughput plateaus

Service time and active capacity are fixed. Added concurrency keeps the two
slots busy but cannot create more model work per second; it mostly adds waiting.
Real engines can improve throughput through batching until another resource
saturates, so the shape must be measured rather than copied from this fixture.

## Correlation contract

The client supplies a unique request ID and W3C-style trace ID. The server
returns and logs them. The verifier requires the exact client request-ID set to
match the server completion log. Aggregate metrics without this path make it
hard to connect a slow user response to a queue event, model execution, or
release.

## Metrics boundary

The supplied Prometheus rules use only simulator metrics. A real deployment must
map the exact versioned engine and DCGM exporter metric names. Do not invent a
query that returns an empty graph and then claim the system is healthy.
