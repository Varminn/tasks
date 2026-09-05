import logging

from llm_router.errors import gateway_error
from llm_router.provider import CompletionResponse, ModelProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes completion requests with automatic failover and rate limiting."""

    def __init__(self, primary: ModelProvider, fallback: ModelProvider, rate_limiter) -> None:
        self._primary = primary
        self._fallback = fallback
        self._rate_limiter = rate_limiter

    async def route(self, api_key: str, prompt: str, model: str, tokens: int = 100) -> dict:
        allowed, used, remaining = self._rate_limiter.check_and_record(api_key, tokens)
        if not allowed:
            return gateway_error(429, "Rate limit exceeded. Please try again later.")

        response = await self._primary.complete(prompt, model)

        if response.status in (429, 408, 503):
            logger.warning(
                "Primary provider %s failed (status %d), failing over to %s",
                self._primary.name, response.status, self._fallback.name,
            )
            response = await self._fallback.complete(prompt, model)

        if response.status == 200:
            return {"response": response.text}

        return gateway_error(502, "All providers unavailable. Please try again later.")
