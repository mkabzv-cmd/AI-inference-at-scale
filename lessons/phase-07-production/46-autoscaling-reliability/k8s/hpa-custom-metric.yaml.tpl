apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: oms-model
  namespace: __NAMESPACE__
spec:
  minReplicas: 1
  maxReplicas: 4
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - {type: Pods, value: 1, periodSeconds: 60}
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
        - {type: Pods, value: 1, periodSeconds: 300}
  metrics:
    - type: Pods
      pods:
        metric:
          name: oms_requests_queued_per_pod
        target:
          type: AverageValue
          averageValue: "4"
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: oms-model
