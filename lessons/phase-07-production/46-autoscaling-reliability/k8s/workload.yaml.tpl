apiVersion: apps/v1
kind: Deployment
metadata:
  name: oms-model
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: oms-model
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: oms-model
  template:
    metadata:
      labels:
        app.kubernetes.io/name: oms-model
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 180
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: model
          image: __MODEL_IMAGE__
          imagePullPolicy: IfNotPresent
          ports:
            - {name: http, containerPort: 8000}
            - {name: metrics, containerPort: 8001}
          resources:
            requests:
              cpu: "2"
              memory: 8Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            limits:
              cpu: "4"
              memory: 16Gi
              nvidia.com/gpu: "1"
          startupProbe:
            httpGet: {path: /health, port: http}
            periodSeconds: 10
            failureThreshold: 90
          readinessProbe:
            httpGet: {path: /ready, port: http}
            periodSeconds: 5
            failureThreshold: 2
          livenessProbe:
            httpGet: {path: /health, port: http}
            periodSeconds: 30
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command:
                  - /bin/sh
                  - -ec
                  - |
                    wget -qO- http://127.0.0.1:8000/drain || true
                    sleep 30
          volumeMounts:
            - {name: runtime, mountPath: /tmp}
      volumes:
        - name: runtime
          emptyDir: {sizeLimit: 2Gi}
---
apiVersion: v1
kind: Service
metadata:
  name: oms-model
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: oms-model
  ports:
    - {name: http, port: 8000, targetPort: http}
    - {name: metrics, port: 8001, targetPort: metrics}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: oms-model
  namespace: __NAMESPACE__
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: oms-model
