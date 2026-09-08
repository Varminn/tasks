from contextlib import asynccontextmanager
import json
import os
import sys

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, ValidationError, field_validator
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llm_router.provider import ModelProvider
from llm_router.rate_limiter import RateLimiter
from llm_router.router import ModelRouter


class CompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    prompt: StrictStr
    model: StrictStr = "gpt-4o-mini"
    estimated_tokens: StrictInt = 100

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value:
            raise ValueError("model must not be empty")
        return value

    @field_validator("estimated_tokens")
    @classmethod
    def validate_estimated_tokens(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("estimated_tokens must be a positive integer")
        return value


def create_app(
    primary: ModelProvider,
    fallback: ModelProvider,
    db_path: str = "llm_router.db",
) -> Starlette:
    limiter = RateLimiter(db_path, max_tokens_per_window=50_000, window_seconds=60)
    router = ModelRouter(primary, fallback, limiter)

    async def completions(request: Request) -> JSONResponse:
        auth = request.headers.get("authorization", "")
        api_key = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if not api_key:
            return JSONResponse(
                {"error": {"code": 401, "message": "Missing API key", "type": "gateway_error"}},
                status_code=401,
            )

        try:
            body = await request.json()
            completion_request = CompletionRequest.model_validate(body)
        except (json.JSONDecodeError, ValidationError, ValueError):
            return JSONResponse(
                {"error": {"code": 400, "message": "Invalid completion request", "type": "gateway_error"}},
                status_code=400,
            )

        result = await router.route(
            api_key,
            completion_request.prompt,
            completion_request.model,
            completion_request.estimated_tokens,
        )
        status = result.get("error", {}).get("code", 200)
        return JSONResponse(result, status_code=status)

    @asynccontextmanager
    async def lifespan(_: Starlette):
        try:
            yield
        finally:
            limiter.close()

    return Starlette(
        routes=[Route("/v1/completions", completions, methods=["POST"])],
        lifespan=lifespan,
    )


def run() -> None:
    try:
        primary = _provider_from_environment("PRIMARY")
        fallback = _provider_from_environment("FALLBACK")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    print("LLM Router listening on http://localhost:3003", file=sys.stderr)
    uvicorn.run(create_app(primary, fallback), host="0.0.0.0", port=3003)


def _provider_from_environment(name: str) -> ModelProvider:
    base_url = os.environ.get(f"LLM_ROUTER_{name}_BASE_URL")
    api_key = os.environ.get(f"LLM_ROUTER_{name}_API_KEY")
    if not base_url or not api_key:
        raise ValueError(
            f"LLM_ROUTER_{name}_BASE_URL and LLM_ROUTER_{name}_API_KEY must be configured"
        )
    return ModelProvider(name.lower(), base_url, api_key)
