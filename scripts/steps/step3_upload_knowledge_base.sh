#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# step3_upload_knowledge_base.sh – Create GCS bucket and upload PDFs
#
# Cost: ~$0.01/month storage for 5 PDFs (negligible)
# Safe to run multiple times — existing bucket is skipped, PDFs overwritten
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

print_header "Step 3 of 6 — Upload Knowledge Base PDFs"

print_info "Uploading 5 PDF docs about the Universe & Planet Zephyria"
print_info "to GCS so Vertex AI Search can index them."
echo ""

# ── Create bucket ─────────────────────────────────────────────────────────
print_step "Checking GCS bucket..."
if gsutil ls -b "gs://${GCS_BUCKET}" &>/dev/null 2>&1; then
  print_skip "Bucket already exists: gs://${GCS_BUCKET}"
else
  gsutil mb \
    -p "${GCP_PROJECT_ID}" \
    -l "${GCP_LOCATION}" \
    -b on \
    "gs://${GCS_BUCKET}"
  print_success "Bucket created: gs://${GCS_BUCKET}"
fi

# ── Upload PDFs ───────────────────────────────────────────────────────────
print_step "Uploading PDFs..."
if [ -d "${PDF_DIR}" ] && ls "${PDF_DIR}"/*.pdf &>/dev/null 2>&1; then
  gsutil -m cp "${PDF_DIR}"/*.pdf "gs://${GCS_BUCKET}/documents/"
  PDF_COUNT=$(ls "${PDF_DIR}"/*.pdf | wc -l | tr -d ' ')
  print_success "${PDF_COUNT} PDFs uploaded to gs://${GCS_BUCKET}/documents/"
  echo ""
  echo "  Files uploaded:"
  ls "${PDF_DIR}"/*.pdf | xargs -I{} basename {} | while read f; do
    echo "    • ${f}"
  done
else
  print_warn "No PDFs found in ${PDF_DIR}"
  echo "    Run this first to generate them:"
  echo "    python scripts/generate_sample_docs.py"
  exit 1
fi

# ── Verify ────────────────────────────────────────────────────────────────
print_step "Verifying upload..."
gsutil ls "gs://${GCS_BUCKET}/documents/"

echo ""
echo "  💰 Cost: ~\$0.01/month for storage"
echo "  ✅ Ready for Step 4"
