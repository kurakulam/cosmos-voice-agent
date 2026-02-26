#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step2_create_service_account.sh – Create service account with IAM roles
#
# Cost: FREE — service accounts have no cost
# Safe to run multiple times — existing account is skipped
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 2 of 6 — Create Service Account"

print_info "A service account is a 'robot identity' for the app."
print_info "It lets Cloud Run talk to Vertex AI Search and Gemini."
echo ""

print_step "Checking if service account exists..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
   --project="${GCP_PROJECT_ID}" &>/dev/null 2>&1; then
  print_skip "Service account already exists: ${SERVICE_ACCOUNT}"
else
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="COSMOS Voice Agent Service Account" \
    --project="${GCP_PROJECT_ID}" \
    --quiet
  print_success "Service account created: ${SERVICE_ACCOUNT}"
fi

print_step "Granting required IAM roles..."
ROLES=(
  "roles/discoveryengine.viewer"   # Read Vertex AI Search
  "roles/aiplatform.user"          # Use Gemini Live API
  "roles/storage.objectViewer"     # Read GCS bucket
  "roles/run.invoker"              # Invoke Cloud Run
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${ROLE}" \
    --quiet 2>/dev/null || true
  echo "    ✓ ${ROLE}"
done

echo ""
echo "  💰 Cost: FREE"
echo "  ✅ Ready for Step 3"
