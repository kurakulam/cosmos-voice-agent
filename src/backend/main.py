"""
Cosmos Voice Agent - Backend
FastAPI server that bridges the browser WebSocket (voice) with:
  - Google Gemini Live API  (real-time speech ↔ speech)
  - Vertex AI Search       (RAG retrieval)

All configuration is read from environment variables (see config.py).
"""

import asyncio
import json
import logging
import os

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse

from config import settings
from rag import VertexSearchRAG
from gemini_live import GeminiLiveSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s – %(message)s")
log = logging.getLogger("cosmos")

app = FastAPI(title="Cosmos Voice Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = VertexSearchRAG(
    project_id=settings.GCP_PROJECT_ID,
    location=settings.GCP_LOCATION,
    data_store_id=settings.VERTEX_SEARCH_DATASTORE_ID,
)

# ─── Locate frontend index.html ───────────────────────────────────────────────
# Search multiple possible locations (local dev vs Docker container)
_BASE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_CANDIDATES = [
    os.path.join(_BASE, "frontend", "dist", "index.html"),
    os.path.join(_BASE, "..", "frontend", "index.html"),
    os.path.join(_BASE, "frontend", "index.html"),
    "/app/frontend/dist/index.html",
]
FRONTEND_HTML = None
for _candidate in _FRONTEND_CANDIDATES:
    if os.path.isfile(_candidate):
        FRONTEND_HTML = _candidate
        log.info(f"Frontend found at: {_candidate}")
        break

if not FRONTEND_HTML:
    log.warning("Frontend index.html not found — root route will return 404")


# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "frontend": FRONTEND_HTML is not None}


# ─── RAG endpoint (REST, for debugging) ───────────────────────────────────────
@app.get("/api/search")
async def search(query: str, top_k: int = 5):
    results = await rag.retrieve(query, top_k=top_k)
    return {"query": query, "results": results}


# ─── Serve frontend ────────────────────────────────────────────────────────────
@app.get("/")
async def serve_root():
    if FRONTEND_HTML and os.path.isfile(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML, media_type="text/html")
    return HTMLResponse("<h1>COSMOS Voice Agent</h1><p>Frontend not found. Check deployment.</p>")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Skip API and WebSocket routes
    if full_path.startswith("api/") or full_path.startswith("ws/") or full_path == "health":
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    if FRONTEND_HTML and os.path.isfile(FRONTEND_HTML):
        return FileResponse(FRONTEND_HTML, media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Frontend not found")


# ─── Voice WebSocket ───────────────────────────────────────────────────────────
@app.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    await ws.accept()
    log.info("WebSocket connected")

    session = None

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "start":
                system_prompt = _build_system_prompt()
                session = GeminiLiveSession(
                    project_id=settings.GCP_PROJECT_ID,
                    location=settings.GCP_LOCATION,
                    model=settings.GEMINI_MODEL,
                    system_prompt=system_prompt,
                    output_audio_callback=lambda chunk: asyncio.ensure_future(
                        ws.send_text(json.dumps({"type": "audio", "data": chunk}))
                    ),
                    transcript_callback=lambda text, final: asyncio.ensure_future(
                        ws.send_text(json.dumps({"type": "transcript", "text": text, "final": final}))
                    ),
                )
                await session.start()
                log.info("Gemini Live session started")

            elif mtype == "audio" and session:
                audio_b64 = msg.get("data", "")
                if audio_b64:
                    await session.send_audio(audio_b64)

            elif mtype == "transcript_query" and session:
                user_text = msg.get("text", "")
                if user_text:
                    chunks = await rag.retrieve(user_text, top_k=settings.RAG_TOP_K)
                    context = _format_rag_context(chunks)
                    await session.inject_context(context)
                    await ws.send_text(json.dumps({"type": "rag_context", "chunks": chunks}))

            elif mtype == "stop":
                if session:
                    await session.stop()
                    session = None
                await ws.send_text(json.dumps({"type": "done"}))
                break

    except WebSocketDisconnect:
        log.info("WebSocket disconnected")
    except Exception as exc:
        log.exception("WebSocket error")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        if session:
            await session.stop()


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    return (
        "You are COSMOS — an intelligent voice assistant specialising in the Universe, "
        "space exploration, and the fascinating world of Planet Zephyria, an inhabited world "
        "340 light-years away. "
        "IMPORTANT: Always respond in English only, regardless of the language the user speaks. "
        "You speak in a warm, engaging, and scientifically accurate manner. "
        "You are given relevant knowledge from a knowledge base before each response. "
        "Use this knowledge to answer questions accurately. If you don't know something, say so. "
        "Keep responses concise and conversational — you are a voice assistant, so avoid "
        "long lists or bullet points. Speak as you would naturally in conversation. "
        "Always stay ready to answer follow-up questions in the same session."
    )


def _format_rag_context(chunks: list) -> str:
    if not chunks:
        return ""
    parts = ["Here is relevant knowledge retrieved for this query:\n"]
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] {c.get('content', '')}")
    return "\n".join(parts)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(settings.PORT),
        reload=settings.DEBUG,
        log_level="info",
    )
