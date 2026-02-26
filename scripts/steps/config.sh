#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# config.sh – Shared configuration for all COSMOS GCP scripts
# Sourced by every step script. Edit values here only.
# ════════════════════════════════════════════════════════════════════════════

# ── GCP Project ─────────────────────────────────────────────────────────────
export GCP_PROJECT_ID="mk-2025-03"
export GCP_LOCATION="us-central1"
export SEARCH_LOCATION="global"          # Vertex AI Search uses 'us' not 'us-central1'

# ── Resource Names ───────────────────────────────────────────────────────────
export GCS_BUCKET="${GCP_PROJECT_ID}-cosmos-knowledge"
export DATASTORE_ID="cosmos-knowledge-base_1772078129175"
export APP_ID="cosmos-voice-agent-app"
export SERVICE_ACCOUNT_NAME="cosmos-voice-agent-sa"
export SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
export CLOUD_RUN_SERVICE="cosmos-voice-agent"
export IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${CLOUD_RUN_SERVICE}"

# ── App Settings ─────────────────────────────────────────────────────────────
export GEMINI_MODEL="gemini-2.0-flash-live-preview"
export GEMINI_VOICE="Aoede"
export RAG_TOP_K="5"

# ── Paths ────────────────────────────────────────────────────────────────────
export SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export PDF_DIR="${ROOT_DIR}/docs/knowledge_base"
export BACKEND_DIR="${ROOT_DIR}/src/backend"
export FRONTEND_DIR="${ROOT_DIR}/src/frontend"

# ── Helpers ──────────────────────────────────────────────────────────────────
print_header() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  printf  "║  %-56s║\n" "$1"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
}

print_success() { echo "  ✅ $1"; }
print_skip()    { echo "  ⏭  $1 — skipping"; }
print_info()    { echo "  ℹ️  $1"; }
print_warn()    { echo "  ⚠️  $1"; }
print_step()    { echo "▶ $1"; }
