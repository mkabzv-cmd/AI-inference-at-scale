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
    app.kubernetes.io/name: comparison-dp
  ports:
    - name: http
      port: 80
      targetPort: 8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comparison-dp
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: comparison-dp
  template:
    metadata:
      labels:
        app.kubernetes.io/name: comparison-dp
        app.kubernetes.io/part-of: oms-distributed-course
        course.lesson: "30"
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
                  app.kubernetes.io/name: comparison-dp
              topologyKey: kubernetes.io/hostname
      tolerations:
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
          securityContext:
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
        - name: vllm
          image: __VLLM_IMAGE__
          imagePullPolicy: IfNotPresent
          command:
            - vllm
            - serve
            - /models/snapshot
            - --served-model-name
            - __SERVED_MODEL__
            - --host
            - 0.0.0.0
            - --port
            - "8000"
            - --max-model-len
            - __MAX_MODEL_LEN__
            - --max-num-seqs
            - __MAX_NUM_SEQS__
          env: *modelEnv
          ports:
            - name: http
              containerPort: 8000
          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
            failureThreshold: 180
          readinessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
            failureThreshold: 3
          resources:
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
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts: *mounts
      volumes:
        - name: model
          emptyDir:
            sizeLimit: __CACHE_SIZE__Gi
        - name: source
          configMap:
            name: lesson-30-source
