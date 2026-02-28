"""
gemini_live.py – Manages a Gemini Live session.

Key design:
- Real mic audio is sent continuously while user speaks
- Keepalive sends silence only when idle for 5s (not continuously)
- Keepalive and real audio never conflict
"""

import asyncio
import base64
import logging
import time
from typing import Callable, Optional

log = logging.getLogger("cosmos.gemini")

SILENCE_100MS = bytes(3200)   # 100ms silence at 16kHz 16-bit mono
KEEPALIVE_INTERVAL = 5.0      # send silence every 5s when idle


class GeminiLiveSession:
    def __init__(self, project_id, location, model, system_prompt,
                 output_audio_callback, transcript_callback, voice="Aoede"):
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
        self._keepalive_task: Optional[asyncio.Task] = None
        self._cm = None
        self._last_audio_sent = 0.0

    async def start(self):
        try:
            import google.genai as genai
            from google.genai.types import (
                LiveConnectConfig, SpeechConfig, VoiceConfig,
                PrebuiltVoiceConfig, Content, Part,
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

            self._cm = self._client.aio.live.connect(model=self.model, config=config)
            self._session = await self._cm.__aenter__()
            self._last_audio_sent = time.monotonic()
            self._recv_task = asyncio.create_task(self._receive_loop())
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            log.info(f"Gemini Live session started with model: {self.model}")

        except Exception as exc:
            log.error(f"Failed to start Gemini Live session: {exc}")
            raise

    async def stop(self):
        for task in [self._keepalive_task, self._recv_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if self._cm and self._session:
            try:
                await self._cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._session = None
        log.info("Gemini Live session stopped")

    async def send_audio(self, audio_b64: str):
        if not self._session:
            return
        try:
            from google.genai.types import Blob
            await self._session.send_realtime_input(
                audio=Blob(
                    data=base64.b64decode(audio_b64),
                    mime_type="audio/pcm;rate=16000"
                )
            )
            self._last_audio_sent = time.monotonic()
        except Exception as exc:
            log.warning(f"send_audio error: {exc}")

    async def inject_context(self, context_text: str):
        if not self._session or not context_text:
            return
        try:
            from google.genai.types import Content, Part
            await self._session.send_client_content(
                turns=Content(
                    role="user",
                    parts=[Part(text=f"[KNOWLEDGE BASE CONTEXT]\n{context_text}")]
                )
            )
        except Exception as exc:
            log.warning(f"inject_context error: {exc}")

    async def _keepalive_loop(self):
        """Send silence only when idle for KEEPALIVE_INTERVAL seconds."""
        try:
            while True:
                await asyncio.sleep(1.0)
                if not self._session:
                    continue
                idle_secs = time.monotonic() - self._last_audio_sent
                if idle_secs >= KEEPALIVE_INTERVAL:
                    try:
                        from google.genai.types import Blob
                        await self._session.send_realtime_input(
                            audio=Blob(data=SILENCE_100MS, mime_type="audio/pcm;rate=16000")
                        )
                        self._last_audio_sent = time.monotonic()
                        log.debug("Keepalive silence sent")
                    except Exception as exc:
                        log.warning(f"Keepalive error: {exc}")
        except asyncio.CancelledError:
            pass

    async def _receive_loop(self):
        if not self._session:
            return
        BATCH_BYTES = 4800
        audio_buffer = bytearray()

        async def flush_audio():
            nonlocal audio_buffer
            if audio_buffer:
                self.output_audio_callback(base64.b64encode(bytes(audio_buffer)).decode())
                audio_buffer = bytearray()

        try:
            async for response in self._session.receive():
                raw_audio = None

                if hasattr(response, "data") and response.data:
                    raw_audio = response.data

                if hasattr(response, "server_content") and response.server_content:
                    sc = response.server_content
                    if hasattr(sc, "model_turn") and sc.model_turn:
                        for part in sc.model_turn.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                raw_audio = part.inline_data.data
                            if hasattr(part, "text") and part.text:
                                self.transcript_callback(part.text, False)
                    if hasattr(sc, "turn_complete") and sc.turn_complete:
                        await flush_audio()
                        self.transcript_callback("", True)
                        log.info("Turn complete — ready for next question")

                if raw_audio:
                    audio_buffer.extend(raw_audio)
                    if len(audio_buffer) >= BATCH_BYTES:
                        await flush_audio()

        except asyncio.CancelledError:
            await flush_audio()
        except Exception as exc:
            log.error(f"Receive loop error: {exc}")
