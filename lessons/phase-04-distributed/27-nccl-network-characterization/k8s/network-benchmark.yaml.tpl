apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "27"
---
apiVersion: v1
kind: Service
metadata:
  name: network-benchmark
  namespace: __NAMESPACE__
spec:
  clusterIP: None
  publishNotReadyAddresses: true
  selector:
    app.kubernetes.io/name: network-benchmark
  ports:
    - name: rendezvous
      port: 29500
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: network-benchmark
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  serviceName: network-benchmark
  replicas: 3
  podManagementPolicy: Parallel
  selector:
    matchLabels:
      app.kubernetes.io/name: network-benchmark
  template:
    metadata:
      labels:
        app.kubernetes.io/name: network-benchmark
        app.kubernetes.io/part-of: oms-distributed-course
        course.lesson: "27"
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
                  app.kubernetes.io/name: network-benchmark
              topologyKey: kubernetes.io/hostname
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      containers:
        - name: rank
          image: __PYTORCH_IMAGE__
          imagePullPolicy: IfNotPresent
          env:
            - name: NCCL_DEBUG
              value: INFO
            - name: NCCL_DEBUG_SUBSYS
              value: INIT,NET,GRAPH,COLL
          command:
            - /bin/bash
            - -ec
            - |
              ordinal="${HOSTNAME##*-}"
              export RANK="$ordinal" LOCAL_RANK=0 WORLD_SIZE=3
              export MASTER_ADDR="network-benchmark-0.network-benchmark.__NAMESPACE__.svc"
              export MASTER_PORT=29500
              python /lesson/nccl_benchmark.py
              touch /tmp/benchmark-succeeded
              sleep infinity
          readinessProbe:
            exec:
              command: ["test", "-f", "/tmp/benchmark-succeeded"]
            periodSeconds: 3
            failureThreshold: 400
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: 8Gi
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
            name: lesson-27-source
