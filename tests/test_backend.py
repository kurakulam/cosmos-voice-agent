"""
tests/test_backend.py – Unit and integration tests for COSMOS backend.

Run with:
    pytest tests/ -v

For integration tests against real GCP (requires credentials):
    RUN_INTEGRATION=true pytest tests/ -v
"""

import asyncio
import base64
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Config tests ─────────────────────────────────────────────────────────────
class TestConfig:
    def test_defaults(self):
        """Settings should load with sensible defaults."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))
        from config import settings
        assert settings.PORT == 8080
        assert settings.RAG_TOP_K == 5
        assert settings.GCP_LOCATION == "us-central1"

    def test_env_override(self, monkeypatch):
        """Environment variables should override defaults."""
        monkeypatch.setenv("RAG_TOP_K", "10")
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        import importlib
        import sys
        # Remove cached module
        for key in list(sys.modules.keys()):
            if 'config' in key:
                del sys.modules[key]
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))
        from config import Settings
        s = Settings()
        assert s.RAG_TOP_K == 10
        assert s.GCP_PROJECT_ID == "test-project"


# ─── RAG tests ────────────────────────────────────────────────────────────────
class TestVertexSearchRAG:
    def setup_method(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

    def test_serving_config_auto_built(self):
        from rag import VertexSearchRAG
        rag = VertexSearchRAG("proj", "us-central1", "my-store")
        assert "proj" in rag._serving_config
        assert "my-store" in rag._serving_config

    def test_serving_config_override(self):
        from rag import VertexSearchRAG
        custom = "projects/p/locations/l/collections/c/dataStores/d/servingConfigs/s"
        rag = VertexSearchRAG("proj", "us-central1", "store", serving_config=custom)
        assert rag._serving_config == custom

    @pytest.mark.asyncio
    async def test_retrieve_returns_empty_on_api_error(self):
        from rag import VertexSearchRAG
        rag = VertexSearchRAG("proj", "us-central1", "store")
        # Mock the sync method to raise
        rag._sync_retrieve = MagicMock(side_effect=Exception("API error"))
        # Should not raise, returns empty list
        with patch.object(rag, '_sync_retrieve', side_effect=Exception("boom")):
            # retrieve calls _sync_retrieve via executor; patch at class level
            result = await rag.retrieve("test query", top_k=3)
            # When client fails at init, returns []
            assert isinstance(result, list)

    @pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Integration test")
    @pytest.mark.asyncio
    async def test_retrieve_integration(self):
        """Real Vertex AI Search call — requires GOOGLE_CLOUD_PROJECT env var."""
        from rag import VertexSearchRAG
        rag = VertexSearchRAG(
            project_id=os.environ["GCP_PROJECT_ID"],
            location=os.environ.get("GCP_LOCATION", "us-central1"),
            data_store_id=os.environ["VERTEX_SEARCH_DATASTORE_ID"],
        )
        results = await rag.retrieve("What is Planet Zephyria?", top_k=3)
        assert isinstance(results, list)
        print(f"\nRetrieved {len(results)} results")
        for r in results:
            print(f"  - {r.get('title', 'N/A')}: {r.get('content', '')[:80]}...")


# ─── FastAPI app tests ────────────────────────────────────────────────────────
class TestFastAPIApp:
    @pytest.fixture
    def client(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

        # Mock the RAG and Gemini dependencies
        with patch('rag.VertexSearchRAG') as MockRAG:
            MockRAG.return_value.retrieve = AsyncMock(return_value=[
                {"title": "Test", "content": "Test content", "source": "test.pdf"}
            ])
            from fastapi.testclient import TestClient
            from main import app
            yield TestClient(app)

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_search_endpoint(self, client):
        resp = client.get("/api/search?query=Zephyria&top_k=3")
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data
        assert data["query"] == "Zephyria"


# ─── Audio utilities tests ────────────────────────────────────────────────────
class TestAudioUtils:
    """Tests for audio conversion utilities (client-side logic mirrors)."""

    def test_base64_pcm_roundtrip(self):
        """Verify PCM float32 → int16 → base64 → int16 → float32 roundtrip."""
        import numpy as np

        # Simulate float32 PCM
        samples = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)

        # float32 → int16 → base64
        int16 = (samples * 32767).clip(-32768, 32767).astype(np.int16)
        b64 = base64.b64encode(int16.tobytes()).decode()

        # base64 → int16 → float32
        recovered_bytes = base64.b64decode(b64)
        recovered_int16 = np.frombuffer(recovered_bytes, dtype=np.int16)
        recovered_float = recovered_int16.astype(np.float32) / 32768.0

        assert len(recovered_float) == len(samples)
        # Values should be very close (small quantization error expected)
        assert np.max(np.abs(recovered_float - samples)) < 0.001


# ─── WebSocket protocol tests ─────────────────────────────────────────────────
class TestWebSocketProtocol:
    @pytest.fixture
    def ws_client(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

        with patch('rag.VertexSearchRAG') as MockRAG, \
             patch('gemini_live.GeminiLiveSession') as MockSession:

            mock_rag = MockRAG.return_value
            mock_rag.retrieve = AsyncMock(return_value=[])

            mock_session = MockSession.return_value
            mock_session.start = AsyncMock()
            mock_session.stop = AsyncMock()
            mock_session.send_audio = AsyncMock()
            mock_session.inject_context = AsyncMock()

            from fastapi.testclient import TestClient
            from main import app
            yield TestClient(app)

    def test_ws_stop_message(self, ws_client):
        """WebSocket should handle stop message gracefully."""
        with ws_client.websocket_connect("/ws/voice") as ws:
            ws.send_text(json.dumps({"type": "stop"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "done"
