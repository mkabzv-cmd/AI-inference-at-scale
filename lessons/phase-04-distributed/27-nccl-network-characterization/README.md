# 27 — Characterize the network with NCCL

**Status:** outline
**Time:** 5 hours
**Compute:** `g3`, approximately 90 GPU-minutes
**Prerequisites:** 24, 26

## Why this matters

Network limits should be measured before model behavior is blamed on an engine.

## Learning outcomes

- Read NCCL topology and transport logs.
- Distinguish latency-sensitive and bandwidth-sensitive message sizes.
- Compare point-to-point, all-reduce, and all-to-all behavior.

## Under the hood

Relate socket transport, message chunking, collective algorithms, synchronization,
and measured algorithm/bus bandwidth.

## Lab outline

1. Build or run pinned NCCL tests.
2. Benchmark two ranks and then three ranks.
3. Compare send/receive with all-reduce.
4. Change one safe topology or placement variable.

## Evidence to collect

- Raw NCCL logs/results
- Node/network topology
- Latency/bandwidth interpretation

## Completion gate

The learner predicts which parallel strategy will suffer most on the measured
network.

## Cleanup

Delete benchmark jobs and return GPU node capacity to zero.
