apiVersion: v1
kind: Namespace
metadata:
  name: oms-l38
  labels:
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: trainer-only
  namespace: oms-l38
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: trainer
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: trainer
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: trainer
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: v1
kind: Service
metadata:
  name: trainer-headless
  namespace: oms-l38
spec:
  clusterIP: None
  publishNotReadyAddresses: true
  selector:
    app.kubernetes.io/name: trainer
  ports:
    - name: c10d
      port: 29500
      targetPort: 29500
---
apiVersion: batch/v1
kind: Job
metadata:
  name: trainer
  namespace: oms-l38
spec:
  completions: 3
  parallelism: 3
  completionMode: Indexed
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: trainer
    spec:
      subdomain: trainer-headless
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 60
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        fsGroupChangePolicy: OnRootMismatch
        seccompProfile:
          type: RuntimeDefault
      nodeSelector:
        node.kubernetes.io/instance-type: __INSTANCE_TYPE__
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app.kubernetes.io/name: trainer
              topologyKey: kubernetes.io/hostname
      containers:
        - name: trainer
          image: __IMAGE_REF__
          imagePullPolicy: IfNotPresent
          command: ["/bin/bash", "-lc"]
          args:
            - >-
              torchrun
              --nnodes=3
              --nproc-per-node=1
              --node-rank="${JOB_COMPLETION_INDEX}"
              --master-addr=trainer-0.trainer-headless.oms-l38.svc.cluster.local
              --master-port=29500
              /opt/course/lesson38/src/fsdp2_checkpoint.py
              --checkpoint /shared/fsdp2-checkpoint
          ports:
            - name: c10d
              containerPort: 29500
          env:
            - name: JOB_COMPLETION_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
            - name: NCCL_DEBUG
              value: INFO
            - name: TORCH_NCCL_ASYNC_ERROR_HANDLING
              value: "1"
          resources:
            requests:
              cpu: "4"
              memory: 20Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "8"
              memory: 28Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: shared
              mountPath: /shared
      volumes:
        - name: shared
          persistentVolumeClaim:
            claimName: __SHARED_CLAIM__
