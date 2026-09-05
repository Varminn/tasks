import sys

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route

from llm_gateway.provider import MockProvider
from llm_gateway.redactor import StreamRedactor


def create_app() -> Starlette:
    async def completions(request: Request) -> StreamingResponse:
        body = await request.json()
        prompt = body.get("prompt", "")

        chunks = body.get(
            "mock_chunks",
            [
                "Hello! Your email ",
                "is alice@example.com and your ",
                "SSN is 123-45-6789. ",
                "Your card is 4111 1111 1111 1111.",
            ],
        )

        provider = MockProvider(chunks)
        redactor = StreamRedactor()

        async def stream_with_redaction():
            async for chunk in provider.stream(prompt):
                safe = redactor.feed(chunk)
                if safe:
                    yield safe
            final = redactor.flush()
            if final:
                yield final

        return StreamingResponse(
            stream_with_redaction(),
            media_type="text/plain",
            headers={"X-Content-Type-Options": "nosniff"},
        )

    return Starlette(routes=[Route("/v1/completions", completions, methods=["POST"])])


def run() -> None:
    print("LLM Gateway listening on http://localhost:3002", file=sys.stderr)
    uvicorn.run(create_app(), host="0.0.0.0", port=3002)
