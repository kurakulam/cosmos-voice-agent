"""
gemini_live.py – Manages a Gemini Live (real-time multimodal) session.
Updated to use correct API for google-genai SDK latest version.
"""

import asyncio
import base64
import logging
from typing import Callable, Optional

log = logging.getLogger("cosmos.gemini")


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
        self._cm = None  # context manager reference

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
            self._recv_task = asyncio.create_task(self._receive_loop())
            log.info("Gemini Live session started")

        except Exception as exc:
            log.error(f"Failed to start Gemini Live session: {exc}")
            raise

    async def stop(self):
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
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
            # Use send_realtime_input for audio chunks (new SDK API)
            await self._session.send_realtime_input(
                audio=base64.b64decode(audio_b64)
            )
        except AttributeError:
            # Fallback for older SDK versions
            try:
                from google.genai import types as gtypes
                # Try different class names across SDK versions
                for cls_name in ["Blob", "MediaChunk"]:
                    if hasattr(gtypes, cls_name):
                        chunk_cls = getattr(gtypes, cls_name)
                        chunk = chunk_cls(
                            data=base64.b64decode(audio_b64),
                            mime_type="audio/pcm;rate=16000"
                        )
                        # Try different send method signatures
                        for input_cls_name in ["RealtimeInput", "LiveClientRealtimeInput"]:
                            if hasattr(gtypes, input_cls_name):
                                input_cls = getattr(gtypes, input_cls_name)
                                await self._session.send(input_cls(media_chunks=[chunk]))
                                return
                        # Direct send with blob
                        await self._session.send({"realtime_input": {"media_chunks": [
                            {"data": base64.b64decode(audio_b64), "mime_type": "audio/pcm;rate=16000"}
                        ]}})
                        return
            except Exception as exc2:
                log.warning(f"send_audio fallback error: {exc2}")
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
        except AttributeError:
            try:
                from google.genai.types import Content, Part
                await self._session.send(
                    Content(role="user", parts=[Part(text=f"[KNOWLEDGE BASE CONTEXT]\n{context_text}")])
                )
            except Exception as exc:
                log.warning(f"inject_context error: {exc}")

    async def _receive_loop(self):
        if not self._session:
            return
        try:
            async for response in self._session.receive():
                # Audio output
                if hasattr(response, "data") and response.data:
                    audio_b64 = base64.b64encode(response.data).decode()
                    self.output_audio_callback(audio_b64)

                # Check server_content for audio and transcript
                if hasattr(response, "server_content") and response.server_content:
                    sc = response.server_content

                    # Audio in model turn parts
                    if hasattr(sc, "model_turn") and sc.model_turn:
                        for part in sc.model_turn.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                audio_b64 = base64.b64encode(part.inline_data.data).decode()
                                self.output_audio_callback(audio_b64)
                            if hasattr(part, "text") and part.text:
                                self.transcript_callback(part.text, False)

                    if hasattr(sc, "turn_complete") and sc.turn_complete:
                        self.transcript_callback("", True)

                # Direct audio attribute (some SDK versions)
                if hasattr(response, "audio") and response.audio:
                    audio_b64 = base64.b64encode(response.audio).decode()
                    self.output_audio_callback(audio_b64)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error(f"Receive loop error: {exc}")
