#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# setup_vertex_search.sh – Create & configure Vertex AI Search data store
#
# Uses the Discovery Engine REST API via gcloud / curl.
# Run AFTER uploading PDFs to GCS.
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

: "${GCP_PROJECT_ID:?'Set GCP_PROJECT_ID'}"
: "${GCP_LOCATION:=global}"
: "${GCS_BUCKET:?'Set GCS_BUCKET'}"
: "${VERTEX_SEARCH_DATASTORE_ID:=cosmos-knowledge-base}"
APP_ID="${VERTEX_SEARCH_DATASTORE_ID}-app"

ACCESS_TOKEN=$(gcloud auth print-access-token)
API_BASE="https://discoveryengine.googleapis.com/v1alpha"
LOCATION="${GCP_LOCATION}"
[[ "${LOCATION}" == "us-central1" ]] && LOCATION="us"
PARENT="projects/${GCP_PROJECT_ID}/locations/${LOCATION}"

echo "▶ Creating Vertex AI Search data store: ${VERTEX_SEARCH_DATASTORE_ID}"

# Create data store
curl -s -X POST \
  "${API_BASE}/${PARENT}/dataStores?dataStoreId=${VERTEX_SEARCH_DATASTORE_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "COSMOS Knowledge Base",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"]
  }' | python3 -m json.tool || true

echo ""
echo "▶ Importing documents from GCS..."

curl -s -X POST \
  "${API_BASE}/${PARENT}/dataStores/${VERTEX_SEARCH_DATASTORE_ID}/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"gcsSource\": {
      \"inputUris\": [\"gs://${GCS_BUCKET}/documents/*.pdf\"],
      \"dataSchema\": \"document\"
    },
    \"reconciliationMode\": \"INCREMENTAL\"
  }" | python3 -m json.tool || true

echo ""
echo "▶ Creating search app..."

curl -s -X POST \
  "${API_BASE}/${PARENT}/collections/default_collection/engines?engineId=${APP_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"displayName\": \"COSMOS Voice Agent\",
    \"dataStoreIds\": [\"${VERTEX_SEARCH_DATASTORE_ID}\"],
    \"solutionType\": \"SOLUTION_TYPE_SEARCH\",
    \"searchEngineConfig\": {
      \"searchTier\": \"SEARCH_TIER_ENTERPRISE\",
      \"searchAddOns\": [\"SEARCH_ADD_ON_LLM\"]
    }
  }" | python3 -m json.tool || true

echo ""
echo "  ✓ Vertex AI Search setup initiated."
echo "  ⏳ Indexing may take 10-30 minutes. Monitor at:"
echo "     https://console.cloud.google.com/gen-app-builder/data-stores"
echo ""
echo "  Serving config resource name (use in VERTEX_SEARCH_SERVING_CONFIG):"
echo "  projects/${GCP_PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${VERTEX_SEARCH_DATASTORE_ID}/servingConfigs/default_serving_config"
