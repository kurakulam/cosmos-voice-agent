#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# create_gcp_resources.sh – Create all GCP resources for COSMOS Voice Agent
#
# Usage:
#   chmod +x scripts/create_gcp_resources.sh
#   ./scripts/create_gcp_resources.sh
#
# What this creates:
#   1. GCS bucket + uploads knowledge base PDFs
#   2. Vertex AI Search data store + app
#   3. Service account with required roles
#   4. Cloud Run service (deploys the app)
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
GCP_PROJECT_ID="mk-2025-03"
GCP_LOCATION="us-central1"
GCS_BUCKET="${GCP_PROJECT_ID}-cosmos-knowledge"
DATASTORE_ID="cosmos-knowledge-base"
APP_ID="cosmos-voice-agent-app"
SERVICE_ACCOUNT_NAME="cosmos-voice-agent-sa"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
CLOUD_RUN_SERVICE="cosmos-voice-agent"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${CLOUD_RUN_SERVICE}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDF_DIR="${SCRIPT_DIR}/../docs/knowledge_base"

# Vertex AI Search uses 'us' or 'eu' not full region names
SEARCH_LOCATION="us"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   COSMOS Voice Agent – GCP Resource Creation             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Project   : ${GCP_PROJECT_ID}"
echo "  Region    : ${GCP_LOCATION}"
echo "  Bucket    : gs://${GCS_BUCKET}"
echo "  Datastore : ${DATASTORE_ID}"
echo ""

# ── Step 1: Set active project ─────────────────────────────────────────────
echo "▶ [1/8] Setting active project..."
gcloud config set project "${GCP_PROJECT_ID}" --quiet
echo "  ✓ Project set to ${GCP_PROJECT_ID}"

# ── Step 2: Enable APIs ────────────────────────────────────────────────────
echo "▶ [2/8] Enabling required APIs (this may take 1-2 minutes)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  --project="${GCP_PROJECT_ID}" \
  --quiet
echo "  ✓ All APIs enabled"

# ── Step 3: Create Service Account ────────────────────────────────────────
echo "▶ [3/8] Creating service account..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  echo "  ✓ Service account already exists — skipping"
else
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="COSMOS Voice Agent Service Account" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  echo "  ✓ Service account created: ${SERVICE_ACCOUNT}"
fi

# Grant required IAM roles
echo "  Granting IAM roles..."
for ROLE in \
  "roles/discoveryengine.viewer" \
  "roles/aiplatform.user" \
  "roles/storage.objectViewer" \
  "roles/run.invoker"; do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${ROLE}" \
    --quiet 2>/dev/null || true
done
echo "  ✓ IAM roles granted"

# ── Step 4: Create GCS Bucket ─────────────────────────────────────────────
echo "▶ [4/8] Creating GCS bucket..."
if gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null 2>&1; then
  echo "  ✓ Bucket already exists — skipping"
else
  gsutil mb \
    -p "${GCP_PROJECT_ID}" \
    -l "${GCP_LOCATION}" \
    -b on \
    "gs://${GCS_BUCKET}"
  echo "  ✓ Bucket created: gs://${GCS_BUCKET}"
fi

# ── Step 5: Upload PDFs ────────────────────────────────────────────────────
echo "▶ [5/8] Uploading knowledge base PDFs..."
if [ -d "${PDF_DIR}" ] && ls "${PDF_DIR}"/*.pdf &>/dev/null 2>&1; then
  gsutil -m cp "${PDF_DIR}"/*.pdf "gs://${GCS_BUCKET}/documents/"
  PDF_COUNT=$(ls "${PDF_DIR}"/*.pdf | wc -l | tr -d ' ')
  echo "  ✓ ${PDF_COUNT} PDFs uploaded to gs://${GCS_BUCKET}/documents/"
else
  echo "  ⚠ No PDFs found in ${PDF_DIR}"
  echo "    Run: python scripts/generate_sample_docs.py"
fi

# ── Step 6: Create Vertex AI Search Data Store ────────────────────────────
echo "▶ [6/8] Creating Vertex AI Search data store..."
ACCESS_TOKEN=$(gcloud auth print-access-token)
API_BASE="https://discoveryengine.googleapis.com/v1alpha"
PARENT="projects/${GCP_PROJECT_ID}/locations/${SEARCH_LOCATION}"

# Check if data store already exists
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}")

if [ "${HTTP_STATUS}" = "200" ]; then
  echo "  ✓ Data store already exists — skipping"
else
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${API_BASE}/${PARENT}/dataStores?dataStoreId=${DATASTORE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "displayName": "COSMOS Knowledge Base",
      "industryVertical": "GENERIC",
      "contentConfig": "CONTENT_REQUIRED",
      "solutionTypes": ["SOLUTION_TYPE_SEARCH"]
    }')

  HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
  if [[ "${HTTP_CODE}" =~ ^2 ]]; then
    echo "  ✓ Data store created: ${DATASTORE_ID}"
  else
    echo "  ⚠ Data store creation returned: ${HTTP_CODE}"
    echo "    (May already exist or be in progress)"
  fi
fi

# ── Step 7: Import documents into data store ──────────────────────────────
echo "▶ [7/8] Importing PDFs into Vertex AI Search..."
IMPORT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"gcsSource\": {
      \"inputUris\": [\"gs://${GCS_BUCKET}/documents/*.pdf\"],
      \"dataSchema\": \"document\"
    },
    \"reconciliationMode\": \"INCREMENTAL\"
  }")

IMPORT_CODE=$(echo "${IMPORT_RESPONSE}" | tail -1)
if [[ "${IMPORT_CODE}" =~ ^2 ]]; then
  echo "  ✓ Import job started"
  echo "  ⏳ Indexing takes 10-30 minutes. Monitor at:"
  echo "     https://console.cloud.google.com/gen-app-builder/data-stores?project=${GCP_PROJECT_ID}"
else
  echo "  ⚠ Import returned: ${IMPORT_CODE} — may already be imported"
fi

# ── Step 8: Build & Deploy to Cloud Run ───────────────────────────────────
echo "▶ [8/8] Building and deploying to Cloud Run..."
echo "  Building Docker image with Cloud Build..."

# Copy frontend into backend before building
mkdir -p "${SCRIPT_DIR}/../src/backend/frontend/dist"
cp "${SCRIPT_DIR}/../src/frontend/index.html" \
   "${SCRIPT_DIR}/../src/backend/frontend/dist/index.html"

gcloud builds submit \
  --tag="${IMAGE_NAME}:latest" \
  --project="${GCP_PROJECT_ID}" \
  "${SCRIPT_DIR}/../src/backend" \
  --quiet

echo "  ✓ Docker image built: ${IMAGE_NAME}:latest"
echo "  Deploying to Cloud Run..."

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
  --set-env-vars="GEMINI_MODEL=gemini-2.0-flash-live-preview" \
  --set-env-vars="GEMINI_VOICE=Aoede" \
  --set-env-vars="RAG_TOP_K=5" \
  --set-env-vars="DEBUG=false" \
  --project="${GCP_PROJECT_ID}" \
  --quiet

SERVICE_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --region="${GCP_LOCATION}" \
  --project="${GCP_PROJECT_ID}" \
  --format="value(status.url)")

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ COSMOS Voice Agent – All Resources Created!          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  GCS Bucket     : gs://${GCS_BUCKET}"
echo "  Datastore ID   : ${DATASTORE_ID}"
echo "  Service Account: ${SERVICE_ACCOUNT}"
echo "  Cloud Run URL  : ${SERVICE_URL}"
echo "  WebSocket URL  : ${SERVICE_URL/https/wss}/ws/voice"
echo ""
echo "  ⏳ NOTE: Vertex AI Search indexing takes 10-30 minutes."
echo "     The app is deployed but RAG won't work until indexing completes."
echo "     Monitor: https://console.cloud.google.com/gen-app-builder/data-stores?project=${GCP_PROJECT_ID}"
echo ""
echo "  💰 To save costs when not in use, run:"
echo "     ./scripts/delete_gcp_resources.sh"
echo ""

# Save config for delete script
cat > "${SCRIPT_DIR}/.cosmos_config" <<EOF
GCP_PROJECT_ID=${GCP_PROJECT_ID}
GCP_LOCATION=${GCP_LOCATION}
GCS_BUCKET=${GCS_BUCKET}
DATASTORE_ID=${DATASTORE_ID}
APP_ID=${APP_ID}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT}
CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE}
IMAGE_NAME=${IMAGE_NAME}
SEARCH_LOCATION=${SEARCH_LOCATION}
SERVICE_URL=${SERVICE_URL}
EOF
echo "  Config saved to scripts/.cosmos_config"
