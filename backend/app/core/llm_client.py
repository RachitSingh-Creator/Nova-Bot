from decimal import Decimal
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

MODEL_COST_PER_1K = {
    "gpt-4o-mini": Decimal("0.0003"),
    "gpt-4o": Decimal("0.01"),
    "gemini-2.5-flash": Decimal("0.0005"),
}


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.default_model = settings.openai_model
        self.default_temperature = settings.default_temperature
        self.default_max_tokens = settings.default_max_tokens
        self.gemini_api_key = settings.gemini_api_key
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None, max_tokens: int | None = None) -> dict[str, Any]:
        used_model = model or self.default_model
        used_temperature = temperature if temperature is not None else self.default_temperature
        used_max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        if used_model.startswith("gemini"):
            return await self._complete_gemini(
                messages=messages,
                model=used_model,
                temperature=used_temperature,
                max_tokens=used_max_tokens,
            )

        response = await self.client.chat.completions.create(
            model=used_model,
            messages=messages,
            temperature=used_temperature,
            max_tokens=used_max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        return {
            "content": content,
            "model": used_model,
            "prompt_tokens": int(usage.prompt_tokens if usage else 0),
            "completion_tokens": int(usage.completion_tokens if usage else 0),
            "total_tokens": int(usage.total_tokens if usage else 0),
        }

    async def _complete_gemini(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is missing in backend/.env")

        system_prompt = ""
        contents = []
        for item in messages:
            role = item.get("role", "user")
            text = item.get("content", "")
            if not text:
                continue
            if role == "system":
                system_prompt = text
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": text}],
                }
            )

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        provider_model = model
        if model in {"gemini-1.5-flash", "gemini-1.5-flash-latest"}:
            # Legacy selection fallback.
            provider_model = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{provider_model}:generateContent"
        headers = {"x-goog-api-key": self.gemini_api_key}
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        parts = []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()

        usage = data.get("usageMetadata", {})
        prompt_tokens = int(usage.get("promptTokenCount", 0) or 0)
        completion_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
        total_tokens = int(usage.get("totalTokenCount", prompt_tokens + completion_tokens) or 0)

        return {
            "content": content,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    async def stream(self, messages: list[dict[str, str]], model: str | None = None, temperature: float | None = None, max_tokens: int | None = None):
        used_model = model or self.default_model
        if used_model.startswith("gemini"):
            result = await self.complete(messages, model=used_model, temperature=temperature, max_tokens=max_tokens)
            for token in result["content"].split(" "):
                if token:
                    class Delta:
                        content = token + " "

                    class Choice:
                        delta = Delta()

                    class Chunk:
                        choices = [Choice()]
                        usage = None

                    yield Chunk()
            class Usage:
                prompt_tokens = result["prompt_tokens"]
                completion_tokens = result["completion_tokens"]
                total_tokens = result["total_tokens"]

            class FinalChunk:
                choices = []
                usage = Usage()

            yield FinalChunk()
            return

        stream = await self.client.chat.completions.create(
            model=used_model,
            messages=messages,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            yield chunk

    @staticmethod
    def estimate_cost(model: str, total_tokens: int) -> Decimal:
        per_1k = MODEL_COST_PER_1K.get(model, Decimal("0.002"))
        return (Decimal(total_tokens) / Decimal(1000) * per_1k).quantize(Decimal("0.0001"))
