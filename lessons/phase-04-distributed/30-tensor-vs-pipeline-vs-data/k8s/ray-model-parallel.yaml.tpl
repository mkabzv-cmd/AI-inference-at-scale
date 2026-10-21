apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "30"
---
apiVersion: v1
kind: Service
metadata:
  name: comparison-api
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    ray.io/cluster: comparison-ray
    ray.io/node-type: head
  ports:
    - name: http
      port: 80
      targetPort: 8000
---
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: comparison-ray
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  rayVersion: "2.59.0"
  enableInTreeAutoscaling: false
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
      num-cpus: "2"
      num-gpus: "1"
    template:
      metadata:
        labels:
          lesson.model-parallel-member: "true"
          app.kubernetes.io/part-of: oms-distributed-course
      spec:
        automountServiceAccountToken: false
        securityContext: &podSecurity
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          fsGroup: 1000
          fsGroupChangePolicy: OnRootMismatch
          seccompProfile:
            type: RuntimeDefault
        affinity: &memberAffinity
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
                    lesson.model-parallel-member: "true"
                topologyKey: kubernetes.io/hostname
        tolerations: &tolerations
          - key: nvidia.com/gpu
            operator: Exists
            effect: NoSchedule
        initContainers:
          - name: stage-model
            image: __VLLM_IMAGE__
            imagePullPolicy: IfNotPresent
            command: ["python", "/lesson/download_model.py"]
            env: &modelEnv
              - name: MODEL_ID
                value: __MODEL_ID__
              - name: MODEL_REVISION
                value: __MODEL_REVISION__
              - name: HF_HOME
                value: /models/hf
            resources:
              requests:
                cpu: "1"
                memory: 1Gi
                ephemeral-storage: __CACHE_SIZE__Gi
              limits:
                cpu: "2"
                memory: 4Gi
                ephemeral-storage: __CACHE_SIZE__Gi
            securityContext: &containerSecurity
              allowPrivilegeEscalation: false
              capabilities:
                drop: ["ALL"]
            volumeMounts: &mounts
              - name: model
                mountPath: /models
              - name: source
                mountPath: /lesson
                readOnly: true
        containers:
          - name: ray-head
            image: __VLLM_IMAGE__
            imagePullPolicy: IfNotPresent
            env: *modelEnv
            ports:
              - name: vllm-api
                containerPort: 8000
            resources: &gpuResources
              requests:
                cpu: "4"
                memory: 8Gi
                ephemeral-storage: __CACHE_SIZE__Gi
                nvidia.com/gpu: "1"
              limits:
                cpu: "8"
                memory: 20Gi
                ephemeral-storage: __CACHE_SIZE__Gi
                nvidia.com/gpu: "1"
            securityContext: *containerSecurity
            volumeMounts: *mounts
        volumes: &volumes
          - name: model
            emptyDir:
              sizeLimit: __CACHE_SIZE__Gi
          - name: source
            configMap:
              name: lesson-30-source
  workerGroupSpecs:
    - groupName: model-workers
      replicas: 2
      minReplicas: 2
      maxReplicas: 2
      rayStartParams:
        num-cpus: "2"
        num-gpus: "1"
      template:
        metadata:
          labels:
            lesson.model-parallel-member: "true"
            app.kubernetes.io/part-of: oms-distributed-course
        spec:
          automountServiceAccountToken: false
          securityContext: *podSecurity
          affinity: *memberAffinity
          tolerations: *tolerations
          initContainers:
            - name: stage-model
              image: __VLLM_IMAGE__
              imagePullPolicy: IfNotPresent
              command: ["python", "/lesson/download_model.py"]
              env: *modelEnv
              resources:
                requests:
                  cpu: "1"
                  memory: 1Gi
                  ephemeral-storage: __CACHE_SIZE__Gi
                limits:
                  cpu: "2"
                  memory: 4Gi
                  ephemeral-storage: __CACHE_SIZE__Gi
              securityContext: *containerSecurity
              volumeMounts: *mounts
          containers:
            - name: ray-worker
              image: __VLLM_IMAGE__
              imagePullPolicy: IfNotPresent
              env: *modelEnv
              resources: *gpuResources
              securityContext: *containerSecurity
              volumeMounts: *mounts
          volumes: *volumes
