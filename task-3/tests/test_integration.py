import httpx
import pytest

from llm_gateway.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestStreamingIntegration:
    @pytest.mark.anyio
    async def test_stream_redacts_email(self, client):
        response = await client.post(
            "/v1/completions",
            json={"prompt": "Tell me about Alice", "mock_chunks": ["Contact ", "alice@example.com", " today"]},
        )
        assert response.status_code == 200
        assert "alice@example.com" not in response.text
        assert "[REDACTED]" in response.text

    @pytest.mark.anyio
    async def test_stream_redacts_ssn_across_chunks(self, client):
        response = await client.post(
            "/v1/completions",
            json={"prompt": "SSN lookup", "mock_chunks": ["SSN: ", "123-45-", "6789."]},
        )
        assert "123-45-6789" not in response.text
        assert "[REDACTED]" in response.text

    @pytest.mark.anyio
    async def test_stream_redacts_credit_card_across_chunks(self, client):
        response = await client.post(
            "/v1/completions",
            json={"prompt": "Card info", "mock_chunks": ["Card: 4111 ", "1111 ", "1111 ", "1111 end"]},
        )
        assert "4111" not in response.text
        assert "[REDACTED]" in response.text

    @pytest.mark.anyio
    async def test_stream_clean_response(self, client):
        response = await client.post(
            "/v1/completions",
            json={"prompt": "hello", "mock_chunks": ["Hello ", "world ", "no PII here"]},
        )
        assert response.text == "Hello world no PII here"

    @pytest.mark.anyio
    async def test_stream_is_streaming_not_buffered(self, client):
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            async with ac.stream(
                "POST",
                "/v1/completions",
                json={"prompt": "test", "mock_chunks": ["chunk1 ", "chunk2 ", "chunk3 "]},
            ) as response:
                chunks = []
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                full = b"".join(chunks).decode()
                assert "chunk1" in full
                assert "chunk3" in full
