from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

import httpx

from nova.voice.command_handler import CommandHandler
from nova.voice.speech_to_text import DeepgramSpeechToText
from nova.voice.text_to_speech import TextToSpeech

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    backend_url: str
    email: str
    password: str
    wake_word: str = "hey nova"
    default_model: str = "gemini-2.5-flash"


class VoiceAssistantController:
    """Wake word -> STT -> command/LLM -> TTS orchestration."""

    def __init__(self, config: VoiceConfig, stt: DeepgramSpeechToText, tts: TextToSpeech) -> None:
        self.config = config
        self.stt = stt
        self.tts = tts
        self.commands = CommandHandler()

        self._http = httpx.AsyncClient(timeout=120)
        self._token: str | None = None
        self._conversation_id: int | None = None
        self._model = config.default_model
        self._running = False

    async def run(self) -> None:
        self._running = True
        await self._login()
        await self._ensure_conversation()
        await self.stt.start()
        await self.tts.start()
        await self.tts.speak("Voice assistant is ready.")

        logger.info("Listening for wake word: '%s'", self.config.wake_word)
        try:
            async for transcript in self.stt.transcripts(final_only=True):
                if not self._running:
                    break
                await self._handle_transcript(transcript)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        if not self._running:
            return
        self._running = False
        await self.stt.stop()
        await self.tts.stop()
        await self._http.aclose()
        logger.info("Voice assistant stopped.")

    async def _login(self) -> None:
        payload = {"email": self.config.email, "password": self.config.password}
        response = await self._http.post(f"{self.config.backend_url}/api/auth/login", json=payload)
        response.raise_for_status()
        self._token = response.json()["access_token"]
        logger.info("Voice assistant authenticated.")

    async def _ensure_conversation(self) -> None:
        assert self._token is not None
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {
            "title": "Voice Session",
            "model": self._model,
            "system_prompt": "I am Nova Bot, your helpful AI assistant.",
        }
        response = await self._http.post(f"{self.config.backend_url}/api/chat/new", headers=headers, json=payload)
        response.raise_for_status()
        self._conversation_id = int(response.json()["id"])
        logger.info("Voice conversation created: %s", self._conversation_id)

    async def _handle_transcript(self, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            return
        lowered = normalized.lower()
        logger.info("Heard: %s", normalized)

        wake = self.config.wake_word.lower()
        if wake not in lowered:
            return

        command_text = lowered.replace(wake, "", 1).strip()
        if not command_text:
            await self.tts.speak("Yes, I am listening.")
            return

        await self.tts.interrupt()

        if "switch to gemini" in command_text:
            self._model = "gemini-2.5-flash"
            await self.tts.speak("Switched model to Gemini 2.5 Flash.")
            return
        if "switch to openai" in command_text:
            self._model = "gpt-4o-mini"
            await self.tts.speak("Switched model to OpenAI GPT 4o mini.")
            return

        cmd_result = self.commands.handle(command_text)
        if cmd_result.executed:
            if cmd_result.response:
                await self.tts.speak(cmd_result.response)
            if cmd_result.should_exit:
                self._running = False
            return

        answer = await self._ask_llm_stream(command_text)
        await self.tts.speak(answer)

    async def _ask_llm_stream(self, user_text: str) -> str:
        assert self._token is not None
        assert self._conversation_id is not None
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {
            "conversation_id": self._conversation_id,
            "message": user_text,
            "model": self._model,
            "temperature": 0.7,
            "max_tokens": 700,
        }

        full_text = ""
        async with self._http.stream(
            "POST",
            f"{self.config.backend_url}/api/chat/send/stream",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                event = json.loads(raw)
                if event.get("type") == "token":
                    full_text += event.get("value", "")
                elif event.get("type") == "error":
                    raise RuntimeError(event.get("value", "Unknown stream error"))
                elif event.get("type") == "done":
                    break

        return full_text.strip() or "I did not get a response."
