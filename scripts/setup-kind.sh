#!/usr/bin/env bash
# ==============================================================================
# Script: setup-kind.sh
# Purpose:
#   Creates a local kind Kubernetes cluster with port mappings for Ingress (80/443),
#   installs NGINX Ingress Controller, and installs Argo CD.
# ==============================================================================

set -euo pipefail

CLUSTER_NAME="preview-cluster"

echo "=========================================================="
echo "Creating kind cluster: ${CLUSTER_NAME}"
echo "=========================================================="

cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

echo "=========================================================="
echo "Installing NGINX Ingress Controller..."
echo "=========================================================="
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

echo "Waiting for NGINX Ingress Controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s

echo "=========================================================="
echo "Installing Argo CD..."
echo "=========================================================="
kubectl create namespace argocd || true
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "Waiting for Argo CD Server..."
kubectl wait --namespace argocd \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=argocd-server \
  --timeout=180s

echo "=========================================================="
echo "Cluster setup complete!"
echo "Argo CD UI: Run 'kubectl port-forward svc/argocd-server -n argocd 8080:443'"
echo "=========================================================="
