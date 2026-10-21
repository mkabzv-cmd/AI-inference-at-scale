apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-course
    open-model-systems.io/lesson: "13"
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
  name: vllm
  namespace: __NAMESPACE__
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        __NODE_SELECTOR_KEY__: __NODE_SELECTOR_VALUE__
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      containers:
        - name: vllm
          image: __IMAGE_URI__
          imagePullPolicy: IfNotPresent
          args:
            - --model
            - Qwen/Qwen2.5-0.5B-Instruct
            - --revision
            - 7ae557604adf67be50417f59c2c2f167def9a775
            - --served-model-name
            - course-model
            - --dtype
            - float16
            - --max-model-len
            - "4096"
            - --gpu-memory-utilization
            - "__GPU_MEMORY_UTILIZATION__"
            - --max-num-seqs
            - "__MAX_NUM_SEQS__"
            - --host
            - 0.0.0.0
            - --port
            - "8000"
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
  name: vllm
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app: vllm
  ports:
    - {name: http, port: 8000, targetPort: http}
