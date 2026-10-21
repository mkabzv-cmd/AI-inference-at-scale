#!/usr/bin/env bash
set -euo pipefail

required=(aws kubectl docker sed)
missing=0

for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$command_name" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

: "${AWS_REGION:?set AWS_REGION, for example us-east-1}"
: "${EKS_CLUSTER:?set EKS_CLUSTER to the intended lab cluster}"

expected_server="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER" \
    --query 'cluster.endpoint' \
    --output text
)"
active_server="$(
  kubectl config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}'
)"
if [[ "$active_server" != "$expected_server" ]]; then
  printf 'refusing to continue: kubectl points at %s\n' "$active_server" >&2
  printf 'but EKS_CLUSTER=%s points at %s\n' \
    "$EKS_CLUSTER" "$expected_server" >&2
  exit 1
fi

printf 'kubectl context: %s\n' "$(kubectl config current-context)"
kubectl cluster-info
kubectl auth can-i create pods --namespace model-storage-lab
kubectl auth can-i create persistentvolumeclaims --namespace model-storage-lab
kubectl auth can-i create storageclasses.storage.k8s.io
kubectl get storageclass
kubectl get csidrivers

if kubectl get csidriver ebs.csi.aws.com >/dev/null 2>&1; then
  printf 'standard Amazon EBS CSI driver found\n'
  kubectl -n kube-system get pods \
    -l 'app.kubernetes.io/name=aws-ebs-csi-driver' -o wide
fi

if kubectl get csidriver ebs.csi.eks.amazonaws.com >/dev/null 2>&1; then
  printf 'EKS Auto Mode EBS CSI driver found\n'
  printf '%s\n' \
    'Auto Mode manages the controller; an aws-ebs-csi-controller Pod is not expected.'
  printf 'Auto Mode nodes currently visible:\n'
  kubectl get nodes \
    -l 'eks.amazonaws.com/compute-type=auto' -o wide
fi

if ! kubectl get csidriver ebs.csi.aws.com >/dev/null 2>&1 &&
  ! kubectl get csidriver ebs.csi.eks.amazonaws.com >/dev/null 2>&1; then
  printf '%s\n' \
    'warning: no expected Amazon EBS CSI driver object was found' >&2
fi
