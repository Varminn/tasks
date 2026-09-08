import os
import tempfile

import httpx
import pytest

from llm_router.main import create_app
from llm_router.provider import CompletionResponse, MockProvider


@pytest.fixture
def app():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as file:
        path = file.name
    primary = MockProvider("primary", CompletionResponse(status=200, text="ok"))
    fallback = MockProvider("fallback", CompletionResponse(status=500))
    yield create_app(primary, fallback, path)
    os.unlink(path)


class TestCompletionEndpoint:
    @pytest.mark.anyio
    async def test_rejects_negative_token_count(self, app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/completions",
                headers={"Authorization": "Bearer tenant-key"},
                json={"prompt": "hello", "estimated_tokens": -1},
            )

        assert response.status_code == 400
        assert response.json() == {
            "error": {
                "code": 400,
                "message": "Invalid completion request",
                "type": "gateway_error",
            }
        }

    @pytest.mark.anyio
    async def test_requires_api_key(self, app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/completions", json={"prompt": "hello"})

        assert response.status_code == 401
        assert response.json()["error"]["type"] == "gateway_error"
