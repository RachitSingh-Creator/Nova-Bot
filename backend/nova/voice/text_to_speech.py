from __future__ import annotations

import asyncio
import io
import logging
import threading
import wave

import pyaudio
import pyttsx3
from openai import OpenAI

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Non-blocking TTS with OpenAI preferred and pyttsx3 fallback."""

    def __init__(self, openai_api_key: str = "", *, voice: str = "alloy", speed: float = 1.0) -> None:
        self.voice = voice
        self.speed = speed
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._stop_speaking = threading.Event()
        self._worker: asyncio.Task | None = None
        self._openai = OpenAI(api_key=openai_api_key) if openai_api_key else None

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._worker = asyncio.create_task(self._run())
        logger.info("TTS worker started.")

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
        logger.info("TTS worker stopped.")

    async def speak(self, text: str) -> None:
        if text.strip():
            await self._queue.put(text.strip())

    async def interrupt(self) -> None:
        self._stop_speaking.set()

    async def _run(self) -> None:
        while True:
            text = await self._queue.get()
            self._stop_speaking.clear()
            await asyncio.to_thread(self._speak_blocking, text)

    def _speak_blocking(self, text: str) -> None:
        if self._openai:
            try:
                self._speak_openai(text)
                return
            except Exception as exc:
                logger.warning("OpenAI TTS failed, using pyttsx3 fallback: %s", exc)
        self._speak_pyttsx3(text)

    def _speak_openai(self, text: str) -> None:
        response = self._openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=self.voice,
            input=text,
            response_format="wav",
            speed=self.speed,
        )

        data: bytes
        if hasattr(response, "read"):
            data = response.read()
        elif hasattr(response, "content"):
            data = response.content
        else:
            data = bytes(response)  # best-effort fallback

        self._play_wav(data)

    def _play_wav(self, wav_bytes: bytes) -> None:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )
            try:
                chunk_size = 1024
                while not self._stop_speaking.is_set():
                    chunk = wf.readframes(chunk_size)
                    if not chunk:
                        break
                    stream.write(chunk)
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()

    def _speak_pyttsx3(self, text: str) -> None:
        engine = pyttsx3.init()
        default_rate = engine.getProperty("rate") or 200
        engine.setProperty("rate", int(default_rate * self.speed))
        engine.say(text)

        speaker = threading.Thread(target=engine.runAndWait, daemon=True)
        speaker.start()
        while speaker.is_alive():
            if self._stop_speaking.is_set():
                engine.stop()
                break
            speaker.join(timeout=0.05)

