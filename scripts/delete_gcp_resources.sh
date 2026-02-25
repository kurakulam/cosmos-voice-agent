#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# delete_gcp_resources.sh – Delete all GCP resources for COSMOS Voice Agent
#
# Run this when you're done testing to avoid ongoing cloud charges.
#
# Usage:
#   chmod +x scripts/delete_gcp_resources.sh
#   ./scripts/delete_gcp_resources.sh
#
# What this deletes:
#   1. Cloud Run service
#   2. Container Registry images
#   3. Vertex AI Search data store + app
#   4. GCS bucket and all PDFs
#   5. Service account
#
# What this KEEPS (to avoid accidental data loss):
#   - Your GCP project itself
#   - APIs (free to have enabled)
#   - IAM roles on the project
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Load config saved by create script, or use defaults ───────────────────
if [ -f "${SCRIPT_DIR}/.cosmos_config" ]; then
  source "${SCRIPT_DIR}/.cosmos_config"
  echo "  Loaded config from scripts/.cosmos_config"
else
  # Defaults — edit these if you didn't use the create script
  GCP_PROJECT_ID="mk-2025-03"
  GCP_LOCATION="us-central1"
  GCS_BUCKET="${GCP_PROJECT_ID}-cosmos-knowledge"
  DATASTORE_ID="cosmos-knowledge-base"
  APP_ID="cosmos-voice-agent-app"
  SERVICE_ACCOUNT="cosmos-voice-agent-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
  CLOUD_RUN_SERVICE="cosmos-voice-agent"
  IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${CLOUD_RUN_SERVICE}"
  SEARCH_LOCATION="us"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   COSMOS Voice Agent – GCP Resource Deletion             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  This will DELETE the following resources:"
echo "  • Cloud Run service  : ${CLOUD_RUN_SERVICE}"
echo "  • Container images   : ${IMAGE_NAME}"
echo "  • Vertex AI Search   : ${DATASTORE_ID}"
echo "  • GCS Bucket         : gs://${GCS_BUCKET}"
echo "  • Service Account    : ${SERVICE_ACCOUNT}"
echo ""
read -r -p "  Are you sure? Type 'yes' to continue: " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "  Aborted."
  exit 0
fi
echo ""

gcloud config set project "${GCP_PROJECT_ID}" --quiet

# ── Step 1: Delete Cloud Run service ──────────────────────────────────────
echo "▶ [1/5] Deleting Cloud Run service..."
if gcloud run services describe "${CLOUD_RUN_SERVICE}" \
   --region="${GCP_LOCATION}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  gcloud run services delete "${CLOUD_RUN_SERVICE}" \
    --region="${GCP_LOCATION}" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  echo "  ✓ Cloud Run service deleted"
else
  echo "  ✓ Cloud Run service not found — skipping"
fi

# ── Step 2: Delete Container Registry images ──────────────────────────────
echo "▶ [2/5] Deleting Container Registry images..."
if gcloud container images list --repository="gcr.io/${GCP_PROJECT_ID}" \
   --format="value(name)" 2>/dev/null | grep -q "${CLOUD_RUN_SERVICE}"; then
  gcloud container images delete "${IMAGE_NAME}:latest" \
    --force-delete-tags \
    --quiet 2>/dev/null || true
  echo "  ✓ Container images deleted"
else
  echo "  ✓ No container images found — skipping"
fi

# ── Step 3: Delete Vertex AI Search app and data store ────────────────────
echo "▶ [3/5] Deleting Vertex AI Search resources..."
ACCESS_TOKEN=$(gcloud auth print-access-token)
API_BASE="https://discoveryengine.googleapis.com/v1alpha"
PARENT="projects/${GCP_PROJECT_ID}/locations/${SEARCH_LOCATION}"

# Delete the search engine/app first
APP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/collections/default_collection/engines/${APP_ID}")

if [ "${APP_STATUS}" = "200" ]; then
  curl -s -X DELETE \
    "${API_BASE}/${PARENT}/collections/default_collection/engines/${APP_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null
  echo "  ✓ Search app deleted"
  sleep 5
else
  echo "  ✓ Search app not found — skipping"
fi

# Delete the data store
DS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}")

if [ "${DS_STATUS}" = "200" ]; then
  curl -s -X DELETE \
    "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null
  echo "  ✓ Vertex AI Search data store deleted"
else
  echo "  ✓ Data store not found — skipping"
fi

# ── Step 4: Delete GCS bucket ─────────────────────────────────────────────
echo "▶ [4/5] Deleting GCS bucket and contents..."
if gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null 2>&1; then
  gsutil -m rm -r "gs://${GCS_BUCKET}" 2>/dev/null || true
  echo "  ✓ GCS bucket deleted: gs://${GCS_BUCKET}"
else
  echo "  ✓ GCS bucket not found — skipping"
fi

# ── Step 5: Delete Service Account ────────────────────────────────────────
echo "▶ [5/5] Deleting service account..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  gcloud iam service-accounts delete "${SERVICE_ACCOUNT}" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  echo "  ✓ Service account deleted"
else
  echo "  ✓ Service account not found — skipping"
fi

# Clean up config file
rm -f "${SCRIPT_DIR}/.cosmos_config"

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ All COSMOS resources deleted — costs stopped!        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Your GCP project (${GCP_PROJECT_ID}) and APIs are kept."
echo "  To redeploy anytime, run:"
echo "     ./scripts/create_gcp_resources.sh"
echo ""
