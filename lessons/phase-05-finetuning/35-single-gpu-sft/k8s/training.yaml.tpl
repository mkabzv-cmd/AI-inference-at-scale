apiVersion: v1
kind: Namespace
metadata:
  name: oms-l35
  labels:
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: offline-trainer
  namespace: oms-l35
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: qwen-sft
  policyTypes: [Ingress, Egress]
  ingress: []
  egress: []
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: sft-output
  namespace: oms-l35
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: __STORAGE_CLASS__
  resources:
    requests:
      storage: 30Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: qwen-sft
  namespace: oms-l35
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: qwen-sft
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
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
      containers:
        - name: trainer
          image: __IMAGE_REF__
          imagePullPolicy: IfNotPresent
          command: ["/bin/bash", "-lc"]
          args:
            - >-
              python /opt/course/lesson33/src/build_dataset.py
              --input /opt/course/lesson33/data/raw/examples.jsonl
              --config /opt/course/lesson33/configs/dataset.json
              --output-dir /work/dataset &&
              python /opt/course/lesson35/src/train_transformers.py
              --config /opt/course/lesson35/configs/sft.json
              --dataset-dir /work/dataset
              --output /work/run
          env:
            - name: HF_HUB_OFFLINE
              value: "1"
            - name: TRANSFORMERS_OFFLINE
              value: "1"
            - name: HF_HOME
              value: /home/learner/.cache/huggingface
            - name: HF_HUB_CACHE
              value: /opt/model-cache
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
            - name: output
              mountPath: /work
      volumes:
        - name: output
          persistentVolumeClaim:
            claimName: sft-output
