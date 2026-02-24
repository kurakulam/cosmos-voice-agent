#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# init_github.sh – Initialize the GitHub repository for COSMOS Voice Agent
#
# Prerequisites:
#   - GitHub CLI (gh) installed: https://cli.github.com/
#   - gh auth login completed
#
# Usage:
#   chmod +x scripts/init_github.sh
#   ./scripts/init_github.sh
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_NAME="cosmos-voice-agent"
REPO_DESC="Real-time voice AI assistant powered by Gemini Live + Vertex AI Search RAG — Universe & Planet Zephyria knowledge"
REPO_TOPICS="gemini vertex-ai rag voice-assistant google-cloud fastapi cloud-run python"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   COSMOS Voice Agent – GitHub Repository Setup       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check gh CLI
if ! command -v gh &>/dev/null; then
  echo "❌ GitHub CLI not found. Install from: https://cli.github.com/"
  exit 1
fi

# Check auth
if ! gh auth status &>/dev/null; then
  echo "❌ Not authenticated. Run: gh auth login"
  exit 1
fi

GITHUB_USER=$(gh api user --jq .login)
echo "  GitHub user: ${GITHUB_USER}"

# Create repository
echo "▶ Creating GitHub repository: ${REPO_NAME}..."
gh repo create "${REPO_NAME}" \
  --description "${REPO_DESC}" \
  --public \
  --source=. \
  --remote=origin \
  --push \
  2>/dev/null || echo "  (repo may already exist — pushing to existing)"

# Set topics
echo "▶ Setting repository topics..."
gh api \
  --method PUT \
  "/repos/${GITHUB_USER}/${REPO_NAME}/topics" \
  --input - <<EOF
{"names": $(echo "${REPO_TOPICS}" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().split()))")}
EOF

# Push code
echo "▶ Pushing code to GitHub..."
cd "$(git rev-parse --show-toplevel)"
git add -A
git commit -m "feat: initial COSMOS Voice Agent project

- FastAPI backend with Gemini Live integration
- Vertex AI Search RAG implementation
- Voice-only UI with starfield space aesthetic
- 5 PDF knowledge docs (Universe + Planet Zephyria)
- Cloud Run deployment via deploy.sh
- GitHub Actions CI/CD pipeline
- Unit and integration tests" 2>/dev/null || echo "  (nothing new to commit)"

git push origin main 2>/dev/null || git push --set-upstream origin main

REPO_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✓ Repository ready!                                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Repository : ${REPO_URL}"
echo "  Clone      : git clone ${REPO_URL}.git"
echo ""
echo "  Next steps:"
echo "  1. Add GitHub Secrets (Settings → Secrets → Actions):"
echo "       GCP_PROJECT_ID, GCP_SA_KEY, SERVICE_ACCOUNT_EMAIL"
echo "       VERTEX_SEARCH_DATASTORE_ID"
echo ""
echo "  2. Generate PDFs:  python scripts/generate_sample_docs.py"
echo "  3. Deploy to GCP:  ./scripts/deploy.sh"
echo ""
