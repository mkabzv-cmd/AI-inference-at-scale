# Profile: aws-g5-single

Reference capability:

- one Kubernetes node;
- one NVIDIA GPU with approximately 24 GB VRAM;
- current accelerated EKS node image;
- enough persistent or ephemeral storage for the selected model profile.

The tested target may be `g5.2xlarge`, but lessons should remain valid for a
comparable GPU. Real account, subnet, role, and cluster identifiers belong only
in local uncommitted configuration.
