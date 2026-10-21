# Lesson 46 solution notes

## Why the CPU signal misses the fixture

The simulated model work reports 35% CPU even while its two conceptual model
slots are overloaded. A CPU-target HPA therefore keeps one replica. This
mirrors GPU-serving cases where queue demand and KV/scheduler capacity can be
the useful signals while container CPU is not saturated.

## Cold-start gap

Queue scaling requests replicas immediately, but they become ready only after
the configured model-load delay. Backpressure and a bounded queue protect the
service during that gap. Scaling cannot repair requests already rejected before
capacity arrives.

## Stabilization

The normal policy adds at most one Pod per interval and waits through an idle
window before scale-down. The deliberate fixture reacts to alternating demand
with no cooldown or stabilization and exceeds the allowed scale-action budget.

## Pod versus node capacity

An HPA or KEDA object changes desired Pods. Pending GPU Pods require compatible
node capacity. A separate node provisioner or managed node-group process must
observe unschedulable demand, launch a node, join it, install/advertise the GPU,
and only then allow model loading. Those delays belong in the scaling timeline.
