import httpx
from dataclasses import dataclass


@dataclass
class CompletionResponse:
    status: int
    text: str | None = None
    error: str | None = None


class ModelProvider:
    """Wraps a single LLM provider endpoint with a configurable timeout."""

    def __init__(self, name: str, base_url: str, api_key: str, timeout_ms: int = 3000) -> None:
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_ms / 1000.0

    @property
    def name(self) -> str:
        return self._name

    async def complete(self, prompt: str, model: str) -> CompletionResponse:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                )
                if response.status_code == 200:
                    try:
                        data = response.json()
                        text = data["choices"][0]["message"]["content"]
                    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                        return CompletionResponse(status=502, error="invalid_provider_response")
                    if not isinstance(text, str):
                        return CompletionResponse(status=502, error="invalid_provider_response")
                    return CompletionResponse(status=200, text=text)
                return CompletionResponse(status=response.status_code, error=f"http_{response.status_code}")
        except httpx.TimeoutException:
            return CompletionResponse(status=408, error="timeout")
        except httpx.RequestError:
            return CompletionResponse(status=503, error="connection_error")


class MockProvider:
    """Mock provider for testing that returns pre-configured responses."""

    def __init__(self, name: str, response: CompletionResponse) -> None:
        self._name = name
        self._response = response

    @property
    def name(self) -> str:
        return self._name

    async def complete(self, prompt: str, model: str) -> CompletionResponse:
        return self._response
