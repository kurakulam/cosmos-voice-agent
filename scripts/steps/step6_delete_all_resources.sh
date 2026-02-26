#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step6_delete_all_resources.sh – Delete ALL GCP resources to stop costs
#
# Run this when you are done testing to avoid ongoing charges.
# You can recreate everything anytime by running steps 1-5 again.
#
# What gets DELETED:
#   ✗ Cloud Run service
#   ✗ Container Registry images
#   ✗ Vertex AI Search data store + app
#   ✗ GCS bucket + PDFs
#   ✗ Service account
#
# What is KEPT:
#   ✓ GCP project
#   ✓ Enabled APIs (free)
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 6 — Delete All GCP Resources"

echo "  ⚠️  This will DELETE the following resources to stop costs:"
echo ""
echo "     ✗ Cloud Run service    : ${CLOUD_RUN_SERVICE}"
echo "     ✗ Container images     : ${IMAGE_NAME}"
echo "     ✗ Vertex AI Search     : ${DATASTORE_ID}"
echo "     ✗ GCS Bucket           : gs://${GCS_BUCKET}"
echo "     ✗ Service Account      : ${SERVICE_ACCOUNT}"
echo ""
echo "  ✓  Your GCP project and APIs will NOT be deleted."
echo ""
read -r -p "  Type 'yes' to confirm deletion: " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "  Aborted — nothing was deleted."
  exit 0
fi
echo ""

gcloud config set project "${GCP_PROJECT_ID}" --quiet

# ── Delete Cloud Run service ──────────────────────────────────────────────
print_step "[1/5] Deleting Cloud Run service..."
if gcloud run services describe "${CLOUD_RUN_SERVICE}" \
   --region="${GCP_LOCATION}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  gcloud run services delete "${CLOUD_RUN_SERVICE}" \
    --region="${GCP_LOCATION}" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  print_success "Cloud Run service deleted"
else
  print_skip "Cloud Run service not found"
fi

# ── Delete Container Registry images ─────────────────────────────────────
print_step "[2/5] Deleting Container Registry images..."
if gcloud container images list \
   --repository="gcr.io/${GCP_PROJECT_ID}" \
   --format="value(name)" 2>/dev/null | grep -q "${CLOUD_RUN_SERVICE}"; then
  gcloud container images delete "${IMAGE_NAME}:latest" \
    --force-delete-tags \
    --quiet 2>/dev/null || true
  print_success "Container images deleted"
else
  print_skip "No container images found"
fi

# ── Delete Vertex AI Search ───────────────────────────────────────────────
print_step "[3/5] Deleting Vertex AI Search resources..."
ACCESS_TOKEN=$(gcloud auth print-access-token)
API_BASE="https://discoveryengine.googleapis.com/v1alpha"
PARENT="projects/${GCP_PROJECT_ID}/locations/${SEARCH_LOCATION}"

# Delete search app first
APP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/collections/default_collection/engines/${APP_ID}")

if [ "${APP_STATUS}" = "200" ]; then
  curl -s -X DELETE \
    "${API_BASE}/${PARENT}/collections/default_collection/engines/${APP_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null
  print_success "Search app deleted"
  sleep 5
else
  print_skip "Search app not found"
fi

# Delete data store
DS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}")

if [ "${DS_STATUS}" = "200" ]; then
  curl -s -X DELETE \
    "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" > /dev/null
  print_success "Vertex AI Search data store deleted"
else
  print_skip "Data store not found"
fi

# ── Delete GCS bucket ─────────────────────────────────────────────────────
print_step "[4/5] Deleting GCS bucket..."
if gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null 2>&1; then
  gsutil -m rm -r "gs://${GCS_BUCKET}" 2>/dev/null || true
  print_success "GCS bucket deleted: gs://${GCS_BUCKET}"
else
  print_skip "GCS bucket not found"
fi

# ── Delete service account ────────────────────────────────────────────────
print_step "[5/5] Deleting service account..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  gcloud iam service-accounts delete "${SERVICE_ACCOUNT}" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  print_success "Service account deleted"
else
  print_skip "Service account not found"
fi

# Clean up state files
rm -f "$(dirname "${BASH_SOURCE[0]}")/.cosmos_state"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ All resources deleted — costs stopped!               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  To redeploy anytime, run steps 1-5 again or:"
echo "  ./scripts/run_all.sh"
echo ""
