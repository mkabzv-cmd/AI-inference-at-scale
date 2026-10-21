apiVersion: apps/v1
kind: Deployment
metadata:
  name: oms-platform
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: oms-platform
    oms.open-model.systems/release-id: __RELEASE_ID__
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: oms-platform
  template:
    metadata:
      labels:
        app.kubernetes.io/name: oms-platform
        oms.open-model.systems/release-id: __RELEASE_ID__
      annotations:
        oms.open-model.systems/model-revision: __MODEL_REVISION__
        oms.open-model.systems/index-version: __INDEX_VERSION__
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: platform
          image: __IMAGE__
          imagePullPolicy: IfNotPresent
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: ["ALL"]}
          ports:
            - {name: http, containerPort: 8000}
          startupProbe:
            httpGet: {path: /healthz, port: http}
            periodSeconds: 10
            failureThreshold: 90
          readinessProbe:
            httpGet: {path: /readyz, port: http}
            periodSeconds: 5
          resources:
            requests: {cpu: "1", memory: 2Gi}
            limits: {cpu: "2", memory: 4Gi}
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {sizeLimit: 256Mi}
---
apiVersion: v1
kind: Service
metadata:
  name: oms-platform
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: oms-platform
  ports:
    - {name: http, port: 8000, targetPort: http}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: __NAMESPACE__
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-authenticated-gateway
  namespace: __NAMESPACE__
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: oms-platform
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              oms.network/role: authenticated-gateway
          podSelector:
            matchLabels:
              oms.network/role: authenticated-gateway
      ports:
        - {protocol: TCP, port: 8000}
