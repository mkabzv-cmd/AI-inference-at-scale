# Lesson 03 solutions

1. `--gpus all` changes runtime/device injection. It does not rebuild the image.
2. A user-space toolkit cannot manufacture hardware, load an absent host kernel
   driver from an unprivileged container, or configure the host OCI runtime.
3. Read `torch.cuda.get_device_capability(index)`, compare the `(major, minor)`
   tuple with a validated minimum, print the mismatch, and exit non-zero.
4. Device-selection syntax belongs to the Docker/NVIDIA runtime interface. Check
   both `torch.cuda.device_count()` and `CUDA_VISIBLE_DEVICES` in the container.
5. Docker run maps roughly to kubelet/containerd; `--gpus` maps to a Pod
   `nvidia.com/gpu` resource request plus device-plugin allocation; host driver
   maps to the accelerated node AMI; image CUDA/framework remains in the Pod
   image; the physical GPU remains the EC2 instance device.
