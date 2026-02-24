#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# deploy.sh – One-shot deploy of COSMOS Voice Agent to Google Cloud Run
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Docker installed (for local builds) OR use Cloud Build
#   - Your GCP project has billing enabled
#
# Usage:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
# Edit these values OR source from .env
: "${GCP_PROJECT_ID:?'Set GCP_PROJECT_ID'}"
: "${GCP_LOCATION:=us-central1}"
: "${VERTEX_SEARCH_DATASTORE_ID:=cosmos-knowledge-base}"
: "${GEMINI_MODEL:=gemini-2.0-flash-live-preview}"
: "${GEMINI_VOICE:=Aoede}"
: "${RAG_TOP_K:=5}"

APP_NAME="cosmos-voice-agent"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${APP_NAME}"
SERVICE_ACCOUNT="${APP_NAME}-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
REGION="${GCP_LOCATION}"
GCS_BUCKET="${GCP_PROJECT_ID}-cosmos-knowledge"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   COSMOS Voice Agent – Deployment Script             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Project  : ${GCP_PROJECT_ID}"
echo "  Region   : ${REGION}"
echo "  Image    : ${IMAGE_NAME}"
echo ""

# ── Step 1: Enable required APIs ──────────────────────────────────────────
echo "▶ Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  --project="${GCP_PROJECT_ID}" \
  --quiet

echo "  ✓ APIs enabled"

# ── Step 2: Create service account ───────────────────────────────────────
echo "▶ Setting up service account..."
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
     --project="${GCP_PROJECT_ID}" &>/dev/null; then
  gcloud iam service-accounts create "${APP_NAME}-sa" \
    --display-name="COSMOS Voice Agent SA" \
    --project="${GCP_PROJECT_ID}"
fi

# Grant required roles
for ROLE in \
  "roles/discoveryengine.viewer" \
  "roles/aiplatform.user" \
  "roles/storage.objectViewer"; do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${ROLE}" \
    --quiet
done

echo "  ✓ Service account configured"

# ── Step 3: Create GCS bucket for knowledge base docs ────────────────────
echo "▶ Creating knowledge base GCS bucket..."
if ! gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null; then
  gsutil mb -p "${GCP_PROJECT_ID}" -l "${REGION}" "gs://${GCS_BUCKET}"
fi
echo "  ✓ Bucket: gs://${GCS_BUCKET}"

# ── Step 4: Upload knowledge base PDFs ───────────────────────────────────
echo "▶ Uploading knowledge base PDFs..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDF_DIR="${SCRIPT_DIR}/../docs/knowledge_base"

if [ -d "${PDF_DIR}" ] && [ "$(ls -A "${PDF_DIR}"/*.pdf 2>/dev/null)" ]; then
  gsutil -m cp "${PDF_DIR}"/*.pdf "gs://${GCS_BUCKET}/documents/"
  echo "  ✓ PDFs uploaded to gs://${GCS_BUCKET}/documents/"
else
  echo "  ⚠ No PDFs found in ${PDF_DIR}. Generate them first:"
  echo "    python scripts/generate_sample_docs.py"
fi

# ── Step 5: Create Vertex AI Search Data Store ───────────────────────────
echo "▶ Setting up Vertex AI Search data store..."
cat <<EOF

  NOTE: Vertex AI Search data store creation requires manual steps in
  the Google Cloud Console or a separate REST API call. Follow these steps:

  1. Go to: https://console.cloud.google.com/gen-app-builder/data-stores
  2. Click "New data store"
  3. Select "Cloud Storage"
  4. Source: gs://${GCS_BUCKET}/documents/
  5. Data store name: ${VERTEX_SEARCH_DATASTORE_ID}
  6. Document type: PDF
  7. Location: global (or ${REGION})
  8. Click "Create"

  Wait for indexing to complete (5-15 min), then press Enter to continue.
EOF
read -r -p "  Press Enter once data store is ready... "

# ── Step 6: Build Docker image with Cloud Build ───────────────────────────
echo "▶ Building Docker image with Cloud Build..."
gcloud builds submit \
  --tag="${IMAGE_NAME}:latest" \
  --project="${GCP_PROJECT_ID}" \
  "${SCRIPT_DIR}/../src/backend"

echo "  ✓ Image built: ${IMAGE_NAME}:latest"

# ── Step 7: Copy frontend into backend serving directory ──────────────────
echo "▶ Preparing frontend assets..."
FRONTEND_SRC="${SCRIPT_DIR}/../src/frontend"
FRONTEND_DEST="${SCRIPT_DIR}/../src/backend/frontend/dist"
mkdir -p "${FRONTEND_DEST}"
cp "${FRONTEND_SRC}/index.html" "${FRONTEND_DEST}/index.html"
echo "  ✓ Frontend assets ready"

# ── Step 8: Deploy to Cloud Run ───────────────────────────────────────────
echo "▶ Deploying to Cloud Run..."
gcloud run deploy "${APP_NAME}" \
  --image="${IMAGE_NAME}:latest" \
  --region="${REGION}" \
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
  --set-env-vars="GCP_LOCATION=${REGION}" \
  --set-env-vars="VERTEX_SEARCH_DATASTORE_ID=${VERTEX_SEARCH_DATASTORE_ID}" \
  --set-env-vars="GEMINI_MODEL=${GEMINI_MODEL}" \
  --set-env-vars="GEMINI_VOICE=${GEMINI_VOICE}" \
  --set-env-vars="RAG_TOP_K=${RAG_TOP_K}" \
  --set-env-vars="DEBUG=false" \
  --project="${GCP_PROJECT_ID}" \
  --quiet

SERVICE_URL=$(gcloud run services describe "${APP_NAME}" \
  --region="${REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✓ COSMOS Voice Agent deployed!                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  URL      : ${SERVICE_URL}"
echo "  WebSocket: ${SERVICE_URL/https/wss}/ws/voice"
echo "  Health   : ${SERVICE_URL}/health"
echo ""
