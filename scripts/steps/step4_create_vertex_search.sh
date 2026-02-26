#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step4_create_vertex_search.sh – Create Vertex AI Search data store
#                                  and trigger PDF indexing
#
# Cost: ~$2-5/month while active
# Indexing takes 10-30 minutes after this step
# Safe to run multiple times — existing data store is skipped
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 4 of 6 — Create Vertex AI Search"

print_info "This creates a semantic search index over the 5 PDFs."
print_info "The app uses this to answer questions accurately (RAG)."
echo ""

ACCESS_TOKEN=$(gcloud auth print-access-token)
API_BASE="https://discoveryengine.googleapis.com/v1alpha"
PARENT="projects/${GCP_PROJECT_ID}/locations/${SEARCH_LOCATION}"

# ── Create data store ─────────────────────────────────────────────────────
print_step "Checking Vertex AI Search data store..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/dataStores/${DATASTORE_ID}")

if [ "${HTTP_STATUS}" = "200" ]; then
  print_skip "Data store already exists: ${DATASTORE_ID}"
else
  print_step "Creating data store: ${DATASTORE_ID}..."
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
    print_success "Data store created: ${DATASTORE_ID}"
    sleep 3
  else
    print_warn "Unexpected response: ${HTTP_CODE}"
    echo "${RESPONSE}" | head -1 | python3 -m json.tool 2>/dev/null || true
    exit 1
  fi
fi

# ── Import documents ──────────────────────────────────────────────────────
print_step "Triggering PDF import from gs://${GCS_BUCKET}/documents/..."
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
  print_success "Import job started successfully"
else
  print_warn "Import response: ${IMPORT_CODE} (may already be importing)"
fi

# ── Create search app ─────────────────────────────────────────────────────
print_step "Creating search app: ${APP_ID}..."
APP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/${PARENT}/collections/default_collection/engines/${APP_ID}")

if [ "${APP_STATUS}" = "200" ]; then
  print_skip "Search app already exists"
else
  APP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${API_BASE}/${PARENT}/collections/default_collection/engines?engineId=${APP_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"displayName\": \"COSMOS Voice Agent\",
      \"dataStoreIds\": [\"${DATASTORE_ID}\"],
      \"solutionType\": \"SOLUTION_TYPE_SEARCH\",
      \"searchEngineConfig\": {
        \"searchTier\": \"SEARCH_TIER_STANDARD\"
      }
    }")

  APP_CODE=$(echo "${APP_RESPONSE}" | tail -1)
  if [[ "${APP_CODE}" =~ ^2 ]]; then
    print_success "Search app created"
  else
    print_warn "App creation response: ${APP_CODE} — may already exist"
  fi
fi

# ── Print serving config ──────────────────────────────────────────────────
echo ""
echo "  📋 Your Vertex AI Search details:"
echo "     Datastore ID   : ${DATASTORE_ID}"
echo "     Serving config : projects/${GCP_PROJECT_ID}/locations/${SEARCH_LOCATION}/collections/default_collection/dataStores/${DATASTORE_ID}/servingConfigs/default_serving_config"
echo ""
echo "  ⏳ Indexing takes 10-30 minutes."
echo "     Monitor at: https://console.cloud.google.com/gen-app-builder/data-stores?project=${GCP_PROJECT_ID}"
echo ""
echo "  💰 Cost: ~\$2-5/month while active"
echo "  ✅ Ready for Step 5 (wait for indexing to complete first)"
