apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-course
    open-model-systems.io/lesson: "15"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: gguf
  namespace: __NAMESPACE__
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: __STORAGE_CLASS__
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama-cpp
  namespace: __NAMESPACE__
spec:
  replicas: 1
  strategy: {type: Recreate}
  selector:
    matchLabels: {app: llama-cpp}
  template:
    metadata:
      labels: {app: llama-cpp}
    spec:
      automountServiceAccountToken: false
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
      initContainers:
        - name: verify-gguf
          image: __IMAGE_URI__
          command: [/bin/bash, -ceu]
          args:
            - |
              target=/models/qwen2.5-0.5b-instruct-q4_k_m.gguf
              expected=74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db
              url=https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf
              if [[ ! -f "$target" ]]; then
                curl --fail --location --retry 3 --output "$target.part" "$url"
                mv "$target.part" "$target"
              fi
              printf '%s  %s\n' "$expected" "$target" | sha256sum --check -
          volumeMounts:
            - {name: gguf, mountPath: /models}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
      containers:
        - name: server
          image: __IMAGE_URI__
          args:
            - --model
            - /models/qwen2.5-0.5b-instruct-q4_k_m.gguf
            - --alias
            - course-model
            - --host
            - 0.0.0.0
            - --port
            - "8000"
            - --ctx-size
            - "4096"
            - --n-gpu-layers
            - "999"
            - --parallel
            - "4"
            - --jinja
          ports:
            - {name: http, containerPort: 8000}
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "6"
              memory: 8Gi
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
          volumeMounts:
            - {name: gguf, mountPath: /models, readOnly: true}
      volumes:
        - name: gguf
          persistentVolumeClaim: {claimName: gguf}
---
apiVersion: v1
kind: Service
metadata:
  name: llama-cpp
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector: {app: llama-cpp}
  ports:
    - {name: http, port: 8000, targetPort: http}
