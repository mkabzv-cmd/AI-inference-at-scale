apiVersion: v1
kind: Namespace
metadata:
  name: oms-l39
  labels:
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-forward-only
  namespace: oms-l39
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: adapted-model
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: oms-l39
      ports:
        - protocol: TCP
          port: 8000
  egress: []
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adapted-model
  namespace: oms-l39
spec:
  replicas: 1
  revisionHistoryLimit: 3
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: adapted-model
  template:
    metadata:
      labels:
        app.kubernetes.io/name: adapted-model
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      nodeSelector:
        node.kubernetes.io/instance-type: __INSTANCE_TYPE__
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      containers:
        - name: engine
          image: __IMAGE_REF__
          imagePullPolicy: IfNotPresent
          args:
            - --model
            - /models/base
            - --served-model-name
            - Qwen/Qwen2.5-0.5B-Instruct
            - --enable-lora
            - --lora-modules
            - oms-operations=/release/adapter
            - --host
            - 0.0.0.0
            - --port
            - "8000"
            - --max-model-len
            - "2048"
          env:
            - name: HOME
              value: /tmp
            - name: HF_HOME
              value: /tmp/huggingface
            - name: HF_HUB_OFFLINE
              value: "1"
            - name: TRANSFORMERS_OFFLINE
              value: "1"
          ports:
            - name: http
              containerPort: 8000
          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
            failureThreshold: 90
          readinessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
            failureThreshold: 6
          resources:
            requests:
              cpu: "4"
              memory: 12Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "8"
              memory: 24Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: model
              mountPath: /models/base
              readOnly: true
            - name: release
              mountPath: /release
              readOnly: true
      volumes:
        - name: model
          persistentVolumeClaim:
            claimName: __MODEL_CLAIM__
        - name: release
          persistentVolumeClaim:
            claimName: __RELEASE_CLAIM__
---
apiVersion: v1
kind: Service
metadata:
  name: adapted-model
  namespace: oms-l39
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: adapted-model
  ports:
    - name: http
      port: 8000
      targetPort: http
