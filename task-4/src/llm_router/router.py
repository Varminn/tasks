import asyncio
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
        try:
            allowed, _, _ = await asyncio.to_thread(
                self._rate_limiter.check_and_record,
                api_key,
                tokens,
            )
        except ValueError:
            return gateway_error(400, "estimated_tokens must be a positive integer.")
        except Exception:
            logger.exception("Rate limiter failed")
            return gateway_error(503, "Rate limiter is temporarily unavailable. Please try again later.")

        if not allowed:
            return gateway_error(429, "Rate limit exceeded. Please try again later.")

        response = await self._complete(self._primary, prompt, model)

        if response.status == 408 or response.status == 429 or response.status >= 500:
            logger.warning(
                "Primary provider %s failed (status %d), failing over to %s",
                self._primary.name, response.status, self._fallback.name,
            )
            response = await self._complete(self._fallback, prompt, model)

        if response.status == 200:
            return {"response": response.text}

        return gateway_error(502, "All providers unavailable. Please try again later.")

    async def _complete(self, provider: ModelProvider, prompt: str, model: str) -> CompletionResponse:
        try:
            return await provider.complete(prompt, model)
        except Exception:
            logger.exception("Provider %s raised an unexpected error", provider.name)
            return CompletionResponse(status=503, error="provider_error")
