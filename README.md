# 🪐 COSMOS Voice Agent

> A real-time voice AI assistant specialising in the Universe and Planet Zephyria —
> powered by **Google Gemini Live** for speech-to-speech AI and
> **Vertex AI Search** for Retrieval-Augmented Generation (RAG).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Cloud Run (HTTPS/WSS)                         │
│                                                                       │
│  ┌─────────────────┐        ┌───────────────────────────────────┐    │
│  │  Frontend (HTML)│◄──────►│      FastAPI Backend              │    │
│  │  Voice-only UI  │  WSS   │                                   │    │
│  │  Web Audio API  │        │  ┌──────────────┐  ┌──────────┐  │    │
│  └─────────────────┘        │  │ Gemini Live  │  │ Vertex   │  │    │
│                             │  │ Session      │  │ AI Search│  │    │
│                             │  │ (Audio I/O)  │  │ (RAG)    │  │    │
│                             │  └──────┬───────┘  └────┬─────┘  │    │
│                             │         │               │         │    │
│                             └─────────┼───────────────┼─────────┘    │
└─────────────────────────────────────── ┼ ──────────────┼ ────────────┘
                                         │               │
                               ┌─────────▼──────┐  ┌────▼──────────────┐
                               │ Gemini 2.0     │  │ Vertex AI Search   │
                               │ Flash Live     │  │ Data Store         │
                               │ (Speech↔Speech)│  │ (PDF Knowledge)    │
                               └────────────────┘  └───────────────────┘
                                                          ▲
                                                    ┌─────┴────┐
                                                    │ GCS Bucket│
                                                    │  5 PDFs   │
                                                    └──────────┘
```

### Data Flow

1. User speaks into browser microphone
2. Web Audio API captures 16-bit PCM at 16 kHz
3. Audio chunks streamed via WebSocket to FastAPI backend
4. Backend streams audio to **Gemini Live** API (real-time STT + LLM)
5. Simultaneously, backend queries **Vertex AI Search** for relevant knowledge
6. Retrieved context injected into Gemini session
7. Gemini responds with audio (24 kHz PCM) streamed back
8. Browser plays audio in real-time

---

## Knowledge Base

Five PDF documents are generated covering:

| File | Content |
|------|---------|
| `01_universe_overview.pdf` | Age, structure, dark matter/energy, fate |
| `02_zephyria_world_guide.pdf` | Planet specs, atmosphere, geography |
| `03_zephyria_life_forms.pdf` | Flora, fauna, Velorian civilization |
| `04_space_exploration_phenomena.pdf` | JWST, black holes, gravitational waves |
| `05_zephyria_faq.pdf` | 18 Q&A pairs optimised for RAG retrieval |

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Google Cloud account** with billing enabled
- **`gcloud` CLI** installed and authenticated
- **Docker** (optional — Cloud Build used in production)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_ORG/cosmos-voice-agent.git
cd cosmos-voice-agent

# Create environment file
cp .env.example .env
# Edit .env with your GCP project ID and settings
```

### 2. Generate knowledge base PDFs

```bash
pip install reportlab
python scripts/generate_sample_docs.py
# → Creates 5 PDFs in docs/knowledge_base/
```

### 3. Set up Google Cloud

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com

# Create GCS bucket
gsutil mb -l us-central1 gs://YOUR_PROJECT-cosmos-knowledge

# Upload PDFs
gsutil -m cp docs/knowledge_base/*.pdf gs://YOUR_PROJECT-cosmos-knowledge/documents/
```

### 4. Create Vertex AI Search Data Store

```bash
# Automated (uses Discovery Engine REST API)
export GCP_PROJECT_ID=your-project-id
export GCS_BUCKET=your-project-cosmos-knowledge
export VERTEX_SEARCH_DATASTORE_ID=cosmos-knowledge-base
chmod +x scripts/setup_vertex_search.sh
./scripts/setup_vertex_search.sh

# OR manually via Console:
# https://console.cloud.google.com/gen-app-builder/data-stores
```

> ⏳ Wait 10-30 minutes for indexing to complete before testing.

### 5. Run locally

```bash
cd src/backend
pip install -r requirements.txt

# Copy frontend
mkdir -p frontend/dist
cp ../frontend/index.html frontend/dist/index.html

# Start server
python main.py
# → Open http://localhost:8080
```

### 6. Deploy to Cloud Run

```bash
# Single command deployment
export GCP_PROJECT_ID=your-project-id
export VERTEX_SEARCH_DATASTORE_ID=cosmos-knowledge-base
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | ✅ | — | Your GCP project ID |
| `GCP_LOCATION` | | `us-central1` | GCP region |
| `VERTEX_SEARCH_DATASTORE_ID` | ✅ | — | Vertex AI Search data store ID |
| `VERTEX_SEARCH_SERVING_CONFIG` | | auto-built | Full serving config resource name |
| `GEMINI_MODEL` | | `gemini-2.0-flash-live-preview` | Gemini model for Live API |
| `GEMINI_VOICE` | | `Aoede` | TTS voice (Aoede/Charon/Fenrir/Kore/Puck) |
| `RAG_TOP_K` | | `5` | Number of knowledge chunks to retrieve |
| `PORT` | | `8080` | HTTP server port |
| `DEBUG` | | `false` | Enable debug logging & hot reload |
| `ALLOWED_ORIGINS` | | `["*"]` | CORS allowed origins (JSON array) |

---

## CI/CD with GitHub Actions

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_SA_KEY` | Service account JSON key (base64) |
| `GCP_LOCATION` | Cloud region |
| `SERVICE_ACCOUNT_EMAIL` | Cloud Run service account email |
| `VERTEX_SEARCH_DATASTORE_ID` | Vertex AI Search store ID |

### Workflow Triggers

- **`push` to `main`** → build, push image, deploy to production
- **Pull Request** → run tests, deploy PR preview environment
- **`push` to `develop`** → run tests only

### Setting up service account for GitHub Actions

```bash
# Create key for GitHub Actions
gcloud iam service-accounts keys create /tmp/sa-key.json \
  --iam-account cosmos-voice-agent-sa@YOUR_PROJECT.iam.gserviceaccount.com

# Add to GitHub secrets as GCP_SA_KEY
cat /tmp/sa-key.json | base64 | pbcopy  # macOS
# Paste into GitHub → Settings → Secrets → Actions → New secret
rm /tmp/sa-key.json
```

---

## Project Structure

```
cosmos-voice-agent/
├── .github/
│   └── workflows/
│       └── cicd.yml              # GitHub Actions CI/CD
├── docs/
│   └── knowledge_base/           # Generated PDF knowledge docs
│       ├── 01_universe_overview.pdf
│       ├── 02_zephyria_world_guide.pdf
│       ├── 03_zephyria_life_forms.pdf
│       ├── 04_space_exploration_phenomena.pdf
│       └── 05_zephyria_faq.pdf
├── scripts/
│   ├── generate_sample_docs.py   # PDF generation script
│   ├── setup_vertex_search.sh    # Vertex AI Search setup
│   └── deploy.sh                 # Full deployment script
├── src/
│   ├── backend/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings from env vars
│   │   ├── rag.py                # Vertex AI Search RAG
│   │   ├── gemini_live.py        # Gemini Live session handler
│   │   ├── requirements.txt      # Python dependencies
│   │   └── Dockerfile            # Multi-stage Docker build
│   └── frontend/
│       └── index.html            # Voice UI (single HTML file)
├── tests/
│   └── test_backend.py           # Unit & integration tests
├── cloudbuild.yaml               # Cloud Build config
├── .env.example                  # Environment template
├── .gitignore
└── README.md
```

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx numpy

# Run unit tests
pytest tests/ -v -k "not integration"

# Run with integration tests (requires real GCP credentials)
export RUN_INTEGRATION=true
export GCP_PROJECT_ID=your-project
export VERTEX_SEARCH_DATASTORE_ID=cosmos-knowledge-base
pytest tests/ -v
```

---

## Voice UI Features

| Feature | Description |
|---------|-------------|
| 🎤 Click to talk | Tap mic button to toggle recording |
| 🔊 Push-to-talk | Hold mic button while speaking |
| ⌨️ Keyboard | Hold `Space` bar to record |
| 🌊 Waveform | Real-time audio visualization |
| 📜 Transcript | Live display of conversation |
| ⬡ Knowledge pill | Shows retrieved RAG context |
| 🌟 Starfield | Animated space background |

---

## Extending the Knowledge Base

To add more documents:

```bash
# Add PDFs to GCS
gsutil cp my-new-doc.pdf gs://YOUR_BUCKET/documents/

# Trigger re-import in Vertex AI Search
# Console → Vertex AI Search → Data Store → Import
# OR use the REST API (see setup_vertex_search.sh)
```

---

## Troubleshooting

**"WebSocket connection failed"**
- Check Cloud Run allows WebSocket (set `--timeout=3600`)
- Ensure `wss://` is used for HTTPS deployments

**"Vertex AI Search returns no results"**
- Wait for indexing to complete (10-30 min after import)
- Verify data store ID matches `VERTEX_SEARCH_DATASTORE_ID`
- Check service account has `discoveryengine.viewer` role

**"Gemini Live session fails"**
- Verify `gemini-2.0-flash-live-preview` is available in your region
- Check Vertex AI API is enabled
- Ensure service account has `aiplatform.user` role

**Microphone not working in browser**
- Site must be served over HTTPS (or localhost)
- Grant microphone permission in browser settings

---

## License

MIT — see LICENSE file.

---

*Built with ❤️ for the cosmos — and for Planet Zephyria, 340 light-years away.*
