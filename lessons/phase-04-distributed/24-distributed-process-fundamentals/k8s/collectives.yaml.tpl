apiVersion: v1
kind: Namespace
metadata:
  name: __NAMESPACE__
  labels:
    app.kubernetes.io/part-of: oms-distributed-course
    course.lesson: "24"
---
apiVersion: v1
kind: Service
metadata:
  name: collectives
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: collectives
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  clusterIP: None
  publishNotReadyAddresses: true
  selector:
    app.kubernetes.io/name: collectives
  ports:
    - name: rendezvous
      port: 29500
      targetPort: 29500
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: collectives
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: collectives
    app.kubernetes.io/part-of: oms-distributed-course
spec:
  serviceName: collectives
  replicas: 3
  podManagementPolicy: Parallel
  selector:
    matchLabels:
      app.kubernetes.io/name: collectives
  template:
    metadata:
      labels:
        app.kubernetes.io/name: collectives
        app.kubernetes.io/part-of: oms-distributed-course
        course.lesson: "24"
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 20
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
                    values:
                      - __NODEGROUP__
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app.kubernetes.io/name: collectives
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
              export RANK="$ordinal"
              export LOCAL_RANK=0
              export WORLD_SIZE=3
              export MASTER_ADDR="collectives-0.collectives.__NAMESPACE__.svc"
              export MASTER_PORT=29500
              export NCCL_DEBUG=WARN
              export TORCH_DISTRIBUTED_DEBUG=DETAIL
              python /lesson/collectives_lab.py \
                --backend nccl \
                --operation all-reduce \
                --elements 1048576 \
                --iterations 5 \
                --warmup 2 \
                --expect-world-size 3 \
                --timeout-seconds 120
              touch /tmp/collective-succeeded
              sleep infinity
          readinessProbe:
            exec:
              command:
                - test
                - -f
                - /tmp/collective-succeeded
            periodSeconds: 2
            failureThreshold: 300
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
            name: collectives-source
