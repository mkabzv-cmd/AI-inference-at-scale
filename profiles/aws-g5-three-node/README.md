# Profile: aws-g5-three-node

Reference capability:

- three separate one-GPU nodes;
- all nodes in one Availability Zone;
- ordinary VPC networking is sufficient for the core learning goals;
- one Pod or distributed rank per node;
- node capacity returns to zero after the lab.

This profile is intentionally network-constrained. It teaches the cost of
collectives and the difference between data, tensor, and pipeline parallelism.
