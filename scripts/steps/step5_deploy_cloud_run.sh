#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step5_deploy_cloud_run.sh – Build Docker image and deploy to Cloud Run
#
# Cost:
#   Cloud Build: ~$0.01-0.03 per build
#   Cloud Run:   $0 when idle (scales to zero), pay only per request
# Run AFTER step4 indexing is complete for full RAG functionality
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 5 of 6 — Build & Deploy to Cloud Run"

print_info "Builds a Docker image from the backend code"
print_info "and deploys it to Cloud Run (serverless — scales to zero)."
echo ""

# ── Copy frontend into backend for serving ────────────────────────────────
print_step "Preparing frontend assets..."
mkdir -p "${BACKEND_DIR}/frontend/dist"
cp "${FRONTEND_DIR}/index.html" "${BACKEND_DIR}/frontend/dist/index.html"
print_success "Frontend copied into backend"

# ── Build Docker image ────────────────────────────────────────────────────
print_step "Building Docker image with Cloud Build..."
print_info "This takes 2-5 minutes..."
echo ""

gcloud builds submit \
  --tag="${IMAGE_NAME}:latest" \
  --project="${GCP_PROJECT_ID}" \
  "${BACKEND_DIR}"

print_success "Docker image built: ${IMAGE_NAME}:latest"

# ── Deploy to Cloud Run ───────────────────────────────────────────────────
print_step "Deploying to Cloud Run..."
gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image="${IMAGE_NAME}:latest" \
  --region="${GCP_LOCATION}" \
  --platform=managed \
  --service-account="${SERVICE_ACCOUNT}" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=3600 \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-env-vars="GCP_LOCATION=${GCP_LOCATION}" \
  --set-env-vars="VERTEX_SEARCH_DATASTORE_ID=${DATASTORE_ID}" \
  --set-env-vars="GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-env-vars="GEMINI_VOICE=${GEMINI_VOICE}" \
  --set-env-vars="RAG_TOP_K=${RAG_TOP_K}" \
  --set-env-vars="DEBUG=false" \
  --project="${GCP_PROJECT_ID}" \
  --quiet

# ── Get service URL ───────────────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --region="${GCP_LOCATION}" \
  --project="${GCP_PROJECT_ID}" \
  --format="value(status.url)")

# Save URL for other scripts
echo "SERVICE_URL=${SERVICE_URL}" >> "$(dirname "${BASH_SOURCE[0]}")/.cosmos_state"

echo ""
echo "  🌐 Your COSMOS Voice Agent is LIVE!"
echo ""
echo "     App URL   : ${SERVICE_URL}"
echo "     WebSocket : ${SERVICE_URL/https/wss}/ws/voice"
echo "     Health    : ${SERVICE_URL}/health"
echo "     RAG Test  : ${SERVICE_URL}/api/search?query=What+is+Zephyria"
echo ""
echo "  💰 Cost: \$0 when idle, ~\$0.10/day with light usage"
echo "  ✅ Step 5 complete — open the URL in your browser!"
