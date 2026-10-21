apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-course
    open-model-systems.io/lesson: "11"
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
  name: transformers-baseline
  namespace: __NAMESPACE__
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: transformers-baseline
  template:
    metadata:
      labels:
        app: transformers-baseline
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 45
      securityContext:
        fsGroup: 10001
        fsGroupChangePolicy: OnRootMismatch
        runAsGroup: 10001
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      nodeSelector:
        __NODE_SELECTOR_KEY__: __NODE_SELECTOR_VALUE__
      containers:
        - name: api
          image: __IMAGE_URI__
          imagePullPolicy: IfNotPresent
          env:
            - {name: MODEL_ID, value: "Qwen/Qwen2.5-0.5B-Instruct"}
            - {name: MODEL_REVISION, value: "7ae557604adf67be50417f59c2c2f167def9a775"}
            - {name: DTYPE, value: "float16"}
            - {name: MAX_MODEL_LEN, value: "4096"}
            - {name: SERIALIZE_GENERATION, value: "__SERIALIZE_GENERATION__"}
            - {name: HF_HOME, value: "/models/huggingface"}
          ports:
            - {name: http, containerPort: 8000}
          resources:
            requests:
              cpu: "2"
              memory: 6Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: 10Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          startupProbe:
            httpGet: {path: /health/ready, port: http}
            periodSeconds: 10
            failureThreshold: 120
          readinessProbe:
            httpGet: {path: /health/ready, port: http}
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet: {path: /health/live, port: http}
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
  name: transformers-baseline
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app: transformers-baseline
  ports:
    - {name: http, port: 8000, targetPort: http}
