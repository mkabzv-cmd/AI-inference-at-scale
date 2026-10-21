apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "26"
---
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: teaching-ray
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "26"
spec:
  rayVersion: "2.59.0"
  enableInTreeAutoscaling: false
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
      num-cpus: "1"
      num-gpus: "0"
    template:
      metadata:
        labels:
          app.kubernetes.io/part-of: oms-distributed-course
          course.lesson: "26"
      spec:
        automountServiceAccountToken: false
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          fsGroup: 1000
          fsGroupChangePolicy: OnRootMismatch
          seccompProfile:
            type: RuntimeDefault
        containers:
          - name: ray-head
            image: __RAY_IMAGE__
            imagePullPolicy: IfNotPresent
            resources:
              requests:
                cpu: "1"
                memory: 2Gi
              limits:
                cpu: "2"
                memory: 4Gi
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop: ["ALL"]
            volumeMounts:
              - name: lesson-source
                mountPath: /lesson
                readOnly: true
        volumes:
          - name: lesson-source
            configMap:
              name: lesson-26-source
  workerGroupSpecs:
    - groupName: one-gpu-workers
      replicas: 3
      minReplicas: 3
      maxReplicas: 3
      rayStartParams:
        num-cpus: "2"
        num-gpus: "1"
      template:
        metadata:
          labels:
            app.kubernetes.io/part-of: oms-distributed-course
            course.lesson: "26"
            lesson.worker-group: one-gpu
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
            fsGroupChangePolicy: OnRootMismatch
            seccompProfile:
              type: RuntimeDefault
          affinity:
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                  - matchExpressions:
                      - key: eks.amazonaws.com/nodegroup
                        operator: In
                        values: [__NODEGROUP__]
            podAntiAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                - labelSelector:
                    matchLabels:
                      lesson.worker-group: one-gpu
                  topologyKey: kubernetes.io/hostname
          tolerations:
            - key: nvidia.com/gpu
              operator: Exists
              effect: NoSchedule
          containers:
            - name: ray-worker
              image: __RAY_IMAGE__
              imagePullPolicy: IfNotPresent
              resources:
                requests:
                  cpu: "2"
                  memory: 4Gi
                  nvidia.com/gpu: "1"
                limits:
                  cpu: "4"
                  memory: 8Gi
                  nvidia.com/gpu: "1"
              securityContext:
                allowPrivilegeEscalation: false
                capabilities:
                  drop: ["ALL"]
