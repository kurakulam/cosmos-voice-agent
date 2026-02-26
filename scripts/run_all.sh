#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# run_all.sh – Master orchestrator for COSMOS Voice Agent GCP deployment
#
# Calls all step scripts in order, or lets you run specific steps.
#
# Usage:
#   ./scripts/run_all.sh              # Run all steps (full deployment)
#   ./scripts/run_all.sh --step 4     # Run only step 4
#   ./scripts/run_all.sh --from 3     # Run from step 3 onwards
#   ./scripts/run_all.sh --delete     # Delete all resources (step 6)
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEPS_DIR="${SCRIPT_DIR}/steps"

# ── Make all step scripts executable ──────────────────────────────────────
chmod +x "${STEPS_DIR}"/*.sh

# ── Step definitions ───────────────────────────────────────────────────────
declare -A STEP_NAMES=(
  [1]="Enable GCP APIs"
  [2]="Create Service Account"
  [3]="Upload Knowledge Base PDFs"
  [4]="Create Vertex AI Search"
  [5]="Build & Deploy to Cloud Run"
  [6]="Delete All Resources"
)

declare -A STEP_COST=(
  [1]="FREE"
  [2]="FREE"
  [3]="~\$0.01/month"
  [4]="~\$2-5/month"
  [5]="\$0 idle / pay-per-use"
  [6]="Stops all costs"
)

# ── Parse arguments ────────────────────────────────────────────────────────
RUN_STEP=""
FROM_STEP=1
TO_STEP=5

while [[ $# -gt 0 ]]; do
  case $1 in
    --step)   RUN_STEP="$2"; shift 2 ;;
    --from)   FROM_STEP="$2"; shift 2 ;;
    --to)     TO_STEP="$2"; shift 2 ;;
    --delete) RUN_STEP=6; shift ;;
    --help|-h)
      echo ""
      echo "Usage:"
      echo "  ./scripts/run_all.sh              # Full deployment (steps 1-5)"
      echo "  ./scripts/run_all.sh --step 4     # Run only step 4"
      echo "  ./scripts/run_all.sh --from 3     # Run steps 3 to 5"
      echo "  ./scripts/run_all.sh --from 3 --to 4  # Run steps 3 and 4"
      echo "  ./scripts/run_all.sh --delete     # Delete all resources"
      echo ""
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Print menu ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   COSMOS Voice Agent – Deployment Orchestrator           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Available steps:"
echo ""
for i in 1 2 3 4 5; do
  echo "  Step ${i}: ${STEP_NAMES[$i]}"
  echo "          Cost: ${STEP_COST[$i]}"
done
echo ""
echo "  Step 6: ${STEP_NAMES[6]}"
echo "          ${STEP_COST[6]}"
echo ""

# ── Determine which steps to run ──────────────────────────────────────────
if [ -n "${RUN_STEP}" ]; then
  # Run single step
  STEPS_TO_RUN=("${RUN_STEP}")
else
  # Run range
  STEPS_TO_RUN=()
  for ((i=FROM_STEP; i<=TO_STEP; i++)); do
    STEPS_TO_RUN+=("$i")
  done
fi

# ── Confirm ────────────────────────────────────────────────────────────────
echo "  Steps to run: ${STEPS_TO_RUN[*]}"
echo ""

if [ "${#STEPS_TO_RUN[@]}" -gt 1 ]; then
  read -r -p "  Press Enter to start, or Ctrl+C to cancel... "
fi

# ── Run steps ──────────────────────────────────────────────────────────────
FAILED=0
for STEP in "${STEPS_TO_RUN[@]}"; do
  SCRIPT="${STEPS_DIR}/step${STEP}_*.sh"

  # Check script exists
  if ! ls ${SCRIPT} &>/dev/null 2>&1; then
    echo "  ❌ No script found for step ${STEP}"
    FAILED=1
    continue
  fi

  SCRIPT_PATH=$(ls ${SCRIPT} | head -1)
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Running Step ${STEP}: ${STEP_NAMES[$STEP]}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  if bash "${SCRIPT_PATH}"; then
    echo ""
    echo "  ✅ Step ${STEP} completed successfully"
  else
    echo ""
    echo "  ❌ Step ${STEP} failed — stopping"
    FAILED=1
    break
  fi

  # Pause between steps (except last)
  if [ "${STEP}" != "${STEPS_TO_RUN[-1]}" ] && [ "${STEP}" != "4" ]; then
    sleep 2
  fi

  # Special pause after step 4 for indexing
  if [ "${STEP}" = "4" ] && [ "${STEPS_TO_RUN[-1]}" != "4" ]; then
    echo ""
    echo "  ⏳ Vertex AI Search indexing has started."
    echo "     It takes 10-30 minutes to complete."
    echo ""
    read -r -p "  Wait for indexing then press Enter to continue to Step 5... "
  fi
done

# ── Final summary ──────────────────────────────────────────────────────────
echo ""
if [ "${FAILED}" = "0" ]; then
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  ✅ All steps completed successfully!                    ║"
  echo "╚══════════════════════════════════════════════════════════╝"

  # Show URL if deployed
  STATE_FILE="${STEPS_DIR}/.cosmos_state"
  if [ -f "${STATE_FILE}" ]; then
    source "${STATE_FILE}"
    echo ""
    echo "  🌐 COSMOS Voice Agent: ${SERVICE_URL}"
  fi
else
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  ❌ Deployment stopped due to an error                   ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Fix the error above and re-run the failed step:"
  echo "  ./scripts/run_all.sh --step ${STEP}"
fi
echo ""
