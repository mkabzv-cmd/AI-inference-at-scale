apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: oms-model
  namespace: __NAMESPACE__
spec:
  scaleTargetRef:
    name: oms-model
  minReplicaCount: 1
  maxReplicaCount: 4
  pollingInterval: 15
  cooldownPeriod: 600
  fallback:
    failureThreshold: 3
    replicas: 1
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          policies:
            - {type: Pods, value: 1, periodSeconds: 60}
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
            - {type: Pods, value: 1, periodSeconds: 300}
  triggers:
    - type: prometheus
      metadata:
        serverAddress: __PROMETHEUS_URL__
        metricName: oms_model_queue
        query: sum(oms_requests_queued{namespace="__NAMESPACE__"})
        threshold: "4"
