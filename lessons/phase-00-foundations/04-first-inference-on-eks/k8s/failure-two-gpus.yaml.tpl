apiVersion: v1
kind: Pod
metadata:
  name: intentional-two-gpus
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-learning
    course.lesson: "04"
    exercise: intentional-unschedulable
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  enableServiceLinks: false
  terminationGracePeriodSeconds: 5
  nodeSelector:
    eks.amazonaws.com/nodegroup: __NODEGROUP__
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: wait
      image: __IMAGE_URI_WITH_DIGEST__
      command: ["/bin/sh", "-c", "sleep 300"]
      resources:
        requests:
          cpu: 10m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 128Mi
          nvidia.com/gpu: "2"
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
