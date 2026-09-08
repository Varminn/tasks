import json

import httpx
from collections.abc import AsyncIterator
from typing import Protocol


class StreamingProvider(Protocol):
    def stream(self, prompt: str, model: str) -> AsyncIterator[str]: ...


class MockProvider:
    """Mock LLM provider that yields pre-configured chunks for testing."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk


class OpenAICompatProvider:
    """Provider for OpenAI-compatible streaming APIs (chat/completions)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def stream(self, prompt: str, model: str = "gpt-4o-mini") -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        break
                    delta = json.loads(data)
                    content = delta.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        yield content
