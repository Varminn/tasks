import sys

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from llm_router.provider import ModelProvider
from llm_router.rate_limiter import RateLimiter
from llm_router.router import ModelRouter


def create_app(db_path: str = "llm_router.db") -> Starlette:
    limiter = RateLimiter(db_path, max_tokens_per_window=50_000, window_seconds=60)
    primary = ModelProvider("primary", "https://api.openai.com/v1", api_key="sk-primary-key")
    fallback = ModelProvider("fallback", "https://api.anthropic.com/v1", api_key="sk-fallback-key")
    router = ModelRouter(primary, fallback, limiter)

    async def completions(request: Request) -> JSONResponse:
        auth = request.headers.get("authorization", "")
        api_key = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if not api_key:
            return JSONResponse(
                {"error": {"code": 401, "message": "Missing API key", "type": "gateway_error"}},
                status_code=401,
            )

        body = await request.json()
        prompt = body.get("prompt", "")
        model = body.get("model", "gpt-4o-mini")
        tokens = body.get("estimated_tokens", 100)

        result = await router.route(api_key, prompt, model, tokens)
        status = result.get("error", {}).get("code", 200)
        return JSONResponse(result, status_code=status)

    return Starlette(routes=[Route("/v1/completions", completions, methods=["POST"])])


def run() -> None:
    print("LLM Router listening on http://localhost:3003", file=sys.stderr)
    uvicorn.run(create_app(), host="0.0.0.0", port=3003)
