from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from nova.voice.assistant_controller import VoiceAssistantController, VoiceConfig
from nova.voice.speech_to_text import DeepgramSpeechToText
from nova.voice.text_to_speech import TextToSpeech


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


async def main() -> None:
    load_dotenv()
    setup_logging()

    config = VoiceConfig(
        backend_url=os.getenv("VOICE_BACKEND_URL", "http://localhost"),
        email=os.getenv("VOICE_USER_EMAIL", ""),
        password=os.getenv("VOICE_USER_PASSWORD", ""),
        wake_word=os.getenv("VOICE_WAKE_WORD", "hey nova"),
        default_model=os.getenv("VOICE_DEFAULT_MODEL", "gemini-2.5-flash"),
    )

    stt = DeepgramSpeechToText(
        api_key=os.getenv("DEEPGRAM_API_KEY", ""),
        model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
    )
    tts = TextToSpeech(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        voice=os.getenv("VOICE_TTS_VOICE", "alloy"),
        speed=float(os.getenv("VOICE_TTS_SPEED", "1.0")),
    )

    assistant = VoiceAssistantController(config=config, stt=stt, tts=tts)
    await assistant.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

