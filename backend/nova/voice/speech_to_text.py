from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator
from urllib.parse import urlencode

import sounddevice as sd
import websockets
from deepgram import DeepgramClient

logger = logging.getLogger(__name__)


class DeepgramSpeechToText:
    """Real-time microphone streaming + transcription via Deepgram."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "nova-2",
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_ms: int = 100,
        language: str = "en",
    ) -> None:
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY is required")

        self.api_key = api_key
        self.model = model
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_ms = chunk_ms
        self.language = language

        # SDK object is kept to satisfy/validate Deepgram SDK integration.
        self.dg_client = DeepgramClient(api_key)

        self._audio_q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=50)
        self._text_q: asyncio.Queue[tuple[str, bool]] = asyncio.Queue(maxsize=200)
        self._stop_event = asyncio.Event()
        self._runner: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _build_ws_url(self) -> str:
        params = {
            "model": self.model,
            "encoding": "linear16",
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "language": self.language,
            "interim_results": "true",
            "punctuate": "true",
            "smart_format": "true",
            "endpointing": "300",
            "no_delay": "true",
        }
        return f"wss://api.deepgram.com/v1/listen?{urlencode(params)}"

    async def start(self) -> None:
        if self._runner and not self._runner.done():
            return
        self._stop_event.clear()
        self._loop = asyncio.get_running_loop()
        self._runner = asyncio.create_task(self._run_forever())
        logger.info("Deepgram STT started.")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._runner:
            self._runner.cancel()
            try:
                await self._runner
            except asyncio.CancelledError:
                pass
        logger.info("Deepgram STT stopped.")

    async def transcripts(self, *, final_only: bool = True) -> AsyncIterator[str]:
        while not self._stop_event.is_set():
            text, is_final = await self._text_q.get()
            if final_only and not is_final:
                continue
            if text.strip():
                yield text.strip()

    async def _run_forever(self) -> None:
        backoff = 1
        while not self._stop_event.is_set():
            try:
                await self._run_once()
                backoff = 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Deepgram connection error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)

    async def _run_once(self) -> None:
        assert self._loop is not None
        ws_url = self._build_ws_url()
        headers = {"Authorization": f"Token {self.api_key}"}

        async with websockets.connect(ws_url, additional_headers=headers, ping_interval=10, ping_timeout=20, max_size=2**23) as ws:
            logger.info("Connected to Deepgram WebSocket.")
            producer = asyncio.create_task(self._send_audio(ws))
            consumer = asyncio.create_task(self._recv_transcripts(ws))
            done, pending = await asyncio.wait({producer, consumer}, return_when=asyncio.FIRST_EXCEPTION)
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc

    async def _send_audio(self, ws: websockets.ClientConnection) -> None:
        assert self._loop is not None

        blocksize = int(self.sample_rate * (self.chunk_ms / 1000))

        def callback(indata, frames, time_info, status) -> None:
            if status:
                logger.warning("Microphone status: %s", status)
            if self._stop_event.is_set():
                return
            payload = bytes(indata)
            try:
                self._loop.call_soon_threadsafe(self._audio_q.put_nowait, payload)
            except asyncio.QueueFull:
                pass

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=blocksize,
            callback=callback,
        ):
            while not self._stop_event.is_set():
                chunk = await self._audio_q.get()
                await ws.send(chunk)

    async def _recv_transcripts(self, ws: websockets.ClientConnection) -> None:
        async for raw in ws:
            if self._stop_event.is_set():
                return

            message = json.loads(raw)
            channel = message.get("channel", {})
            alternatives = channel.get("alternatives", [])
            if not alternatives:
                continue

            transcript = alternatives[0].get("transcript", "").strip()
            if not transcript:
                continue

            is_final = bool(message.get("is_final") or message.get("speech_final"))
            try:
                self._text_q.put_nowait((transcript, is_final))
            except asyncio.QueueFull:
                logger.warning("Transcript queue full; dropping text.")

