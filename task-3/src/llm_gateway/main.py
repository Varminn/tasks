import os
import sys

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from llm_gateway.provider import MockProvider, OpenAICompatProvider, StreamingProvider
from llm_gateway.redactor import StreamRedactor

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def create_app(
    provider: StreamingProvider | None = None,
    *,
    default_model: str | None = None,
) -> Starlette:
    if provider is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            provider = OpenAICompatProvider(
                api_key,
                os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            )

    configured_model = default_model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    async def completions(request: Request) -> Response:
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(_gateway_error(400, "Request body must be valid JSON."), status_code=400)

        if not isinstance(body, dict):
            return JSONResponse(_gateway_error(400, "Request body must be a JSON object."), status_code=400)

        prompt = body.get("prompt", "")
        if not isinstance(prompt, str):
            return JSONResponse(_gateway_error(400, "prompt must be a string."), status_code=400)

        if "mock_chunks" in body:
            chunks = body["mock_chunks"]
            if not isinstance(chunks, list) or not all(isinstance(chunk, str) for chunk in chunks):
                return JSONResponse(
                    _gateway_error(400, "mock_chunks must be an array of strings."),
                    status_code=400,
                )
            upstream_stream = MockProvider(chunks).stream(prompt)
        elif provider is None:
            return JSONResponse(
                _gateway_error(503, "No LLM provider is configured."),
                status_code=503,
            )
        else:
            model = body.get("model", configured_model)
            if not isinstance(model, str) or not model:
                return JSONResponse(_gateway_error(400, "model must be a non-empty string."), status_code=400)
            upstream_stream = provider.stream(prompt, model)

        redactor = StreamRedactor()

        async def stream_with_redaction():
            async for chunk in upstream_stream:
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


def _gateway_error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message, "type": "gateway_error"}}


def run() -> None:
    print("LLM Gateway listening on http://localhost:3002", file=sys.stderr)
    uvicorn.run(create_app(), host="0.0.0.0", port=3002)
