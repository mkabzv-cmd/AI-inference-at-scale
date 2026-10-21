apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-course
    open-model-systems.io/lesson: "14"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
  namespace: __NAMESPACE__
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: __STORAGE_CLASS__
  resources:
    requests:
      storage: 20Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sglang
  namespace: __NAMESPACE__
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: sglang
  template:
    metadata:
      labels:
        app: sglang
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        __NODE_SELECTOR_KEY__: __NODE_SELECTOR_VALUE__
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      containers:
        - name: sglang
          image: __IMAGE_URI__
          imagePullPolicy: IfNotPresent
          command: [python3, -m, sglang.launch_server]
          args:
            - --model-path
            - Qwen/Qwen2.5-0.5B-Instruct
            - --revision
            - 7ae557604adf67be50417f59c2c2f167def9a775
            - --served-model-name
            - course-model
            - --dtype
            - float16
            - --context-length
            - "4096"
            - --mem-fraction-static
            - "__MEM_FRACTION_STATIC__"
            - --max-running-requests
            - "__MAX_RUNNING_REQUESTS__"
            - --host
            - 0.0.0.0
            - --port
            - "8000"
            - --enable-metrics
__RADIX_CACHE_ARG__
          env:
            - {name: HF_HOME, value: /models/huggingface}
          ports:
            - {name: http, containerPort: 8000}
          resources:
            requests:
              cpu: "2"
              memory: 8Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "6"
              memory: 16Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          startupProbe:
            httpGet: {path: /health, port: http}
            periodSeconds: 10
            failureThreshold: 120
          readinessProbe:
            httpGet: {path: /health, port: http}
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet: {path: /health, port: http}
            periodSeconds: 15
            failureThreshold: 3
          volumeMounts:
            - {name: cache, mountPath: /models}
      volumes:
        - name: cache
          persistentVolumeClaim:
            claimName: model-cache
---
apiVersion: v1
kind: Service
metadata:
  name: sglang
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app: sglang
  ports:
    - {name: http, port: 8000, targetPort: http}
