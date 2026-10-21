apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: open-model-systems-learning
    course.lesson: "04"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tiny-gpt2
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: tiny-gpt2
    app.kubernetes.io/part-of: open-model-systems-learning
    course.lesson: "04"
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: tiny-gpt2
  template:
    metadata:
      labels:
        app.kubernetes.io/name: tiny-gpt2
        app.kubernetes.io/part-of: open-model-systems-learning
        course.lesson: "04"
    spec:
      automountServiceAccountToken: false
      enableServiceLinks: false
      terminationGracePeriodSeconds: 30
      nodeSelector:
        eks.amazonaws.com/nodegroup: __NODEGROUP__
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: server
          image: __IMAGE_URI_WITH_DIGEST__
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: REQUIRE_CUDA
              value: "true"
            - name: HOME
              value: /tmp
          resources:
            requests:
              cpu: "1"
              memory: 2Gi
            limits:
              cpu: "2"
              memory: 4Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          startupProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 5
            failureThreshold: 120
            timeoutSeconds: 2
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 5
            failureThreshold: 3
            timeoutSeconds: 2
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            failureThreshold: 3
            timeoutSeconds: 2
          volumeMounts:
            - name: temporary
              mountPath: /tmp
      volumes:
        - name: temporary
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: tiny-gpt2
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: tiny-gpt2
    app.kubernetes.io/part-of: open-model-systems-learning
    course.lesson: "04"
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: tiny-gpt2
  ports:
    - name: http
      port: 80
      targetPort: http
