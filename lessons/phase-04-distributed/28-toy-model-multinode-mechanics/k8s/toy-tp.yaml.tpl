apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "28"
---
apiVersion: v1
kind: Service
metadata:
  name: toy-tp
  namespace: __NAMESPACE__
spec:
  clusterIP: None
  publishNotReadyAddresses: true
  selector:
    app.kubernetes.io/name: toy-tp
  ports:
    - name: rendezvous
      port: 29500
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: toy-tp
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  serviceName: toy-tp
  replicas: 3
  podManagementPolicy: Parallel
  selector:
    matchLabels:
      app.kubernetes.io/name: toy-tp
  template:
    metadata:
      labels:
        app.kubernetes.io/name: toy-tp
        app.kubernetes.io/part-of: oms-distributed-course
        course.lesson: "28"
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
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
                  app.kubernetes.io/name: toy-tp
              topologyKey: kubernetes.io/hostname
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      containers:
        - name: rank
          image: __PYTORCH_IMAGE__
          imagePullPolicy: IfNotPresent
          command:
            - /bin/bash
            - -ec
            - |
              ordinal="${HOSTNAME##*-}"
              export RANK="$ordinal" LOCAL_RANK=0 WORLD_SIZE=3
              export MASTER_ADDR="toy-tp-0.toy-tp.__NAMESPACE__.svc"
              export MASTER_PORT=29500
              export NCCL_DEBUG=WARN
              python /lesson/toy_tp.py \
                --backend nccl \
                --output /tmp/summary.json
              touch /tmp/toy-succeeded
              sleep infinity
          readinessProbe:
            exec:
              command: ["test", "-f", "/tmp/toy-succeeded"]
            periodSeconds: 2
            failureThreshold: 300
          resources:
            requests:
              cpu: "1"
              memory: 2Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "2"
              memory: 4Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: source
              mountPath: /lesson
              readOnly: true
      volumes:
        - name: source
          configMap:
            name: lesson-28-source
