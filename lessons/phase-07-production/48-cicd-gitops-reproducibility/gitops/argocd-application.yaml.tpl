apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: oms-platform-__ENVIRONMENT__
  namespace: argocd
spec:
  project: oms-platform
  source:
    repoURL: __REPOSITORY_URL__
    targetRevision: __SOURCE_REVISION__
    path: __MANIFEST_PATH__
  destination:
    server: https://kubernetes.default.svc
    namespace: oms-platform-__ENVIRONMENT__
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - PruneLast=true
