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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_eks_target
assert_namespace_owned_or_absent
assert_storageclass_owned_or_absent model-cache-gp3
assert_storageclass_owned_or_absent model-cache-gp3-auto

require_kube_permission() {
  if ! kubectl auth can-i "$@" --quiet; then
    printf 'Kubernetes authorization denied: kubectl auth can-i %s\n' \
      "$*" >&2
    return 1
  fi
  printf 'Kubernetes authorization allows: %s\n' "$*"
}

printf 'kubectl context: %s\n' "$(kubectl config current-context)"
kubectl cluster-info
require_kube_permission create namespaces
require_kube_permission create pods --namespace model-storage-lab
require_kube_permission delete namespaces
require_kube_permission create persistentvolumeclaims --namespace model-storage-lab
require_kube_permission delete persistentvolumeclaims --namespace model-storage-lab
require_kube_permission list persistentvolumes
require_kube_permission create storageclasses.storage.k8s.io
require_kube_permission delete storageclasses.storage.k8s.io
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
