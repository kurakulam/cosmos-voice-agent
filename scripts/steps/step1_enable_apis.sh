#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step1_enable_apis.sh – Enable all required GCP APIs
#
# Cost: FREE — enabling APIs has no cost
# Safe to run multiple times — already-enabled APIs are skipped
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 1 of 6 — Enable GCP APIs"

print_step "Setting active project to ${GCP_PROJECT_ID}..."
gcloud config set project "${GCP_PROJECT_ID}" --quiet
print_success "Project set"

print_step "Enabling required APIs..."
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

print_success "All APIs enabled:"
echo "    • Cloud Run"
echo "    • Cloud Build"
echo "    • Container Registry"
echo "    • Vertex AI Search (Discovery Engine)"
echo "    • Vertex AI"
echo "    • Cloud Storage"
echo "    • IAM"
echo ""
echo "  💰 Cost: FREE"
echo "  ✅ Ready for Step 2"
