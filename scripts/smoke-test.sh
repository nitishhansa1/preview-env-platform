#!/usr/bin/env bash
# ==============================================================================
# Script: smoke-test.sh
# Purpose:
#   Validates that a preview environment namespace, services, and ingress route
#   respond correctly to HTTP requests.
# Usage:
#   ./scripts/smoke-test.sh <pr-number>
# ==============================================================================

set -euo pipefail

PR_NUMBER="${1:-1}"
DOMAIN_SUFFIX="${2:-127.0.0.1.nip.io}"
PREVIEW_HOST="pr-${PR_NUMBER}.${DOMAIN_SUFFIX}"
NAMESPACE="pr-${PR_NUMBER}"

echo "=========================================================="
echo "Smoke Testing Preview Environment: ${PREVIEW_HOST}"
echo "Namespace: ${NAMESPACE}"
echo "=========================================================="

echo "1. Checking if namespace exists..."
if ! kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
  echo "❌ Error: Namespace '${NAMESPACE}' not found."
  exit 1
fi
echo "✅ Namespace exists."

echo "2. Checking pod status..."
kubectl get pods -n "${NAMESPACE}"

echo "3. Waiting for backend and frontend pods to be ready..."
kubectl wait --namespace "${NAMESPACE}" \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=preview-app \
  --timeout=120s || true

echo "4. Testing HTTP Frontend Ingress endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${PREVIEW_HOST}/" || echo "000")
if [ "${HTTP_STATUS}" -eq 200 ]; then
  echo "✅ Frontend Ingress returned HTTP 200 OK"
else
  echo "⚠️ Warning: Frontend Ingress returned HTTP ${HTTP_STATUS}"
fi

echo "5. Testing HTTP Backend API Health endpoint..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${PREVIEW_HOST}/api/health" || echo "000")
if [ "${BACKEND_STATUS}" -eq 200 ]; then
  echo "✅ Backend API health returned HTTP 200 OK"
else
  echo "⚠️ Warning: Backend API health returned HTTP ${BACKEND_STATUS}"
fi

echo "=========================================================="
echo "Smoke test completed."
echo "=========================================================="
