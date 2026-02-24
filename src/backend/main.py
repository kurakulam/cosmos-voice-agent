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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ─── RAG endpoint (REST, for debugging) ───────────────────────────────────────
@app.get("/api/search")
async def search(query: str, top_k: int = 5):
    results = await rag.retrieve(query, top_k=top_k)
    return {"query": query, "results": results}


# ─── Voice WebSocket ───────────────────────────────────────────────────────────
@app.websocket("/ws/voice")
async def voice_ws(ws: WebSocket):
    """
    Protocol (JSON-framed binary or JSON messages):
      Client → Server:
        { "type": "start" }                        – begin session
        { "type": "audio", "data": "<b64 pcm>" }   – raw audio chunk (16-bit PCM, 16 kHz mono)
        { "type": "stop" }                         – end session

      Server → Client:
        { "type": "audio", "data": "<b64 pcm>" }   – Gemini response audio
        { "type": "transcript", "text": "..." }    – interim/final transcript
        { "type": "rag_context", "chunks": [...] } – retrieved knowledge
        { "type": "error", "message": "..." }
        { "type": "done" }
    """
    await ws.accept()
    log.info("WebSocket connected")

    session: GeminiLiveSession | None = None

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "start":
                # Build system prompt with RAG context placeholder
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
                audio_b64: str = msg.get("data", "")
                if not audio_b64:
                    continue

                # --- RAG: retrieve on each user utterance (lightweight) ---
                # We'll also do a RAG call when we get a transcript
                await session.send_audio(audio_b64)

            elif mtype == "transcript_query" and session:
                # Client sends the recognized text so we can enrich context
                user_text: str = msg.get("text", "")
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


# ─── Serve frontend (production) ───────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = os.path.join(FRONTEND_DIR, "index.html")
        return FileResponse(index)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    return (
        "You are COSMOS — an intelligent voice assistant specialising in the Universe, "
        "space exploration, and the fascinating world of Planet Zephyria, an inhabited world "
        "340 light-years away. You speak in a warm, engaging, and scientifically accurate manner. "
        "You are given relevant knowledge from a knowledge base before each response. "
        "Use this knowledge to answer questions accurately. If you don't know something, say so. "
        "Keep responses concise and conversational — you are a voice assistant, so avoid "
        "long lists or bullet points. Speak as you would naturally in conversation."
    )


def _format_rag_context(chunks: list[dict]) -> str:
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
