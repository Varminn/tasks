import asyncio
import os
import tempfile

import pytest

from llm_router.provider import CompletionResponse, MockProvider
from llm_router.rate_limiter import RateLimiter
from llm_router.router import ModelRouter


@pytest.fixture
def limiter():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    limiter = RateLimiter(path, max_tokens_per_window=10_000, window_seconds=60)
    yield limiter
    os.unlink(path)


class TestModelRouter:
    @pytest.mark.anyio
    async def test_primary_success(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=200, text="Hello!"))
        fallback = MockProvider("fallback", CompletionResponse(status=500))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert result == {"response": "Hello!"}

    @pytest.mark.anyio
    async def test_primary_429_fails_over(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=429, error="rate limited"))
        fallback = MockProvider("fallback", CompletionResponse(status=200, text="Fallback!"))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert result == {"response": "Fallback!"}

    @pytest.mark.anyio
    async def test_primary_timeout_fails_over(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=408, error="timeout"))
        fallback = MockProvider("fallback", CompletionResponse(status=200, text="Fallback!"))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert result == {"response": "Fallback!"}

    @pytest.mark.anyio
    async def test_primary_503_fails_over(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=503, error="unavailable"))
        fallback = MockProvider("fallback", CompletionResponse(status=200, text="Fallback!"))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert result == {"response": "Fallback!"}

    @pytest.mark.anyio
    async def test_primary_500_fails_over(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=500, error="upstream failure"))
        fallback = MockProvider("fallback", CompletionResponse(status=200, text="Fallback!"))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert result == {"response": "Fallback!"}

    @pytest.mark.anyio
    async def test_both_fail_returns_sanitized_error(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=500, error="Internal traceback details"))
        fallback = MockProvider("fallback", CompletionResponse(status=500, error="stack_trace_here"))
        router = ModelRouter(primary, fallback, limiter)
        result = await router.route("key1", "test", "model", 100)
        assert "error" in result
        assert result["error"]["code"] == 502
        assert "Internal traceback" not in str(result)
        assert "stack_trace" not in str(result)

    @pytest.mark.anyio
    async def test_rate_limit_blocks_before_provider_call(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=200, text="ok"))
        fallback = MockProvider("fallback", CompletionResponse(status=500))
        router = ModelRouter(primary, fallback, limiter)

        for _ in range(100):
            await router.route("key1", "test", "model", 100)

        result = await router.route("key1", "test", "model", 100)
        assert "error" in result
        assert result["error"]["code"] == 429

    @pytest.mark.anyio
    async def test_rate_limit_per_key(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=200, text="ok"))
        fallback = MockProvider("fallback", CompletionResponse(status=500))
        router = ModelRouter(primary, fallback, limiter)

        for _ in range(100):
            await router.route("key1", "test", "model", 100)

        result2 = await router.route("key2", "test", "model", 100)
        assert result2 == {"response": "ok"}

    @pytest.mark.anyio
    async def test_concurrent_requests_cannot_exceed_token_limit(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as file:
            path = file.name
        limiter = RateLimiter(path, max_tokens_per_window=1000, window_seconds=60)
        primary = MockProvider("primary", CompletionResponse(status=200, text="ok"))
        fallback = MockProvider("fallback", CompletionResponse(status=500))
        router = ModelRouter(primary, fallback, limiter)

        try:
            results = await asyncio.gather(
                *(router.route("key1", "test", "model", 100) for _ in range(20))
            )
        finally:
            limiter.close()
            os.unlink(path)

        assert sum(result == {"response": "ok"} for result in results) == 10
        assert sum(result.get("error", {}).get("code") == 429 for result in results) == 10

    @pytest.mark.anyio
    async def test_negative_token_count_returns_sanitized_client_error(self, limiter):
        primary = MockProvider("primary", CompletionResponse(status=200, text="ok"))
        fallback = MockProvider("fallback", CompletionResponse(status=500))
        router = ModelRouter(primary, fallback, limiter)

        result = await router.route("key1", "test", "model", -1)
        assert result == {
            "error": {
                "code": 400,
                "message": "estimated_tokens must be a positive integer.",
                "type": "gateway_error",
            }
        }
