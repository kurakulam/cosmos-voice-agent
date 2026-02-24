"""
config.py – All application settings read from environment variables.
Provides sensible defaults for local development.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Google Cloud ────────────────────────────────────────────────────────
    GCP_PROJECT_ID: str = "your-gcp-project-id"
    GCP_LOCATION: str = "us-central1"

    # ── Vertex AI Search ────────────────────────────────────────────────────
    VERTEX_SEARCH_DATASTORE_ID: str = "cosmos-knowledge-base"
    # Full resource name override (optional — auto-built if not set)
    VERTEX_SEARCH_SERVING_CONFIG: str = ""

    # ── Gemini Live ─────────────────────────────────────────────────────────
    GEMINI_MODEL: str = "gemini-2.0-flash-live-preview"
    # Voice name for Gemini TTS output
    GEMINI_VOICE: str = "Aoede"

    # ── RAG ─────────────────────────────────────────────────────────────────
    RAG_TOP_K: int = 5

    # ── App ─────────────────────────────────────────────────────────────────
    PORT: int = 8080
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
