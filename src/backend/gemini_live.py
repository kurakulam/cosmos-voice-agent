"""
gemini_live.py – Manages a Gemini Live (real-time multimodal) session.

Gemini Live API allows streaming audio in ↔ audio out in near-realtime.
We connect via the google-genai SDK (google-generativeai >= 0.8).
"""

import asyncio
import base64
import logging
from typing import Callable, Awaitable, Optional

log = logging.getLogger("cosmos.gemini")


class GeminiLiveSession:
    """
    Manages a single Gemini Multimodal Live session.

    Audio format expectations:
        Input:  16-bit PCM, mono, 16 kHz  (base64-encoded)
        Output: 16-bit PCM, mono, 24 kHz  (base64-encoded, sent via callback)
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        model: str,
        system_prompt: str,
        output_audio_callback: Callable[[str], None],
        transcript_callback: Callable[[str, bool], None],
        voice: str = "Aoede",
    ):
        self.project_id = project_id
        self.location = location
        self.model = model
        self.system_prompt = system_prompt
        self.voice = voice
        self.output_audio_callback = output_audio_callback
        self.transcript_callback = transcript_callback

        self._session = None
        self._client = None
        self._recv_task: Optional[asyncio.Task] = None
        self._context_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        """Initialize the Gemini Live session."""
        try:
            import google.genai as genai
            from google.genai.types import (
                LiveConnectConfig,
                SpeechConfig,
                VoiceConfig,
                PrebuiltVoiceConfig,
                Content,
                Part,
            )

            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )

            config = LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=SpeechConfig(
                    voice_config=VoiceConfig(
                        prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=self.voice)
                    )
                ),
                system_instruction=Content(parts=[Part(text=self.system_prompt)]),
            )

            self._session = await self._client.aio.live.connect(
                model=self.model, config=config
            ).__aenter__()

            # Start background receive loop
            self._recv_task = asyncio.create_task(self._receive_loop())
            log.info("Gemini Live session started")

        except ImportError:
            raise RuntimeError(
                "google-genai not installed. Run: pip install google-genai"
            )
        except Exception as exc:
            log.error(f"Failed to start Gemini Live session: {exc}")
            raise

    async def stop(self):
        """Close the Gemini Live session."""
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None

        log.info("Gemini Live session stopped")

    async def send_audio(self, audio_b64: str):
        """Send a chunk of base64-encoded PCM audio to Gemini."""
        if not self._session:
            return
        try:
            from google.genai.types import RealtimeInput, MediaChunk

            await self._session.send(
                RealtimeInput(
                    media_chunks=[
                        MediaChunk(
                            data=base64.b64decode(audio_b64),
                            mime_type="audio/pcm;rate=16000",
                        )
                    ]
                )
            )
        except Exception as exc:
            log.warning(f"send_audio error: {exc}")

    async def inject_context(self, context_text: str):
        """Inject RAG context as a system-side turn."""
        if not self._session or not context_text:
            return
        try:
            from google.genai.types import Content, Part

            await self._session.send(
                Content(
                    role="user",
                    parts=[
                        Part(
                            text=(
                                f"[KNOWLEDGE BASE CONTEXT — use this to answer the user's question]\n"
                                f"{context_text}"
                            )
                        )
                    ],
                )
            )
        except Exception as exc:
            log.warning(f"inject_context error: {exc}")

    async def _receive_loop(self):
        """Background loop that reads responses from Gemini and fires callbacks."""
        if not self._session:
            return

        try:
            async for response in self._session.receive():
                # Audio output
                if response.data:
                    audio_b64 = base64.b64encode(response.data).decode()
                    self.output_audio_callback(audio_b64)

                # Transcript (server-side VAD)
                if response.server_content:
                    sc = response.server_content
                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if hasattr(part, "text") and part.text:
                                self.transcript_callback(part.text, False)

                    if sc.turn_complete:
                        self.transcript_callback("", True)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error(f"Receive loop error: {exc}")
