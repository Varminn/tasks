from json import JSONDecodeError
import os
import sys

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from pydantic import ValidationError

from mcp_gateway.auth import parse_bearer_token
from mcp_gateway.models import JsonRpcRequest, jsonrpc_error
from mcp_gateway.proxy import McpProxy


def create_app(
    downstream_url: str = "http://localhost:3001/rpc",
    jwt_signing_key: str | None = None,
) -> Starlette:
    if not jwt_signing_key:
        raise ValueError("jwt_signing_key is required")

    proxy = McpProxy(downstream_url)

    async def rpc_handler(request: Request) -> JSONResponse:
        auth_header = request.headers.get("authorization", "")
        try:
            claims = parse_bearer_token(auth_header, jwt_signing_key)
        except ValueError:
            return JSONResponse(
                jsonrpc_error(None, -32001, "Unauthorized"),
                status_code=401,
            )

        try:
            body = await request.json()
            rpc_request = JsonRpcRequest.model_validate(body)
        except (JSONDecodeError, ValidationError):
            return JSONResponse(
                jsonrpc_error(None, -32600, "Invalid JSON-RPC request"),
                status_code=400,
            )

        result = await proxy.handle(rpc_request, claims.role)
        return JSONResponse(result)

    return Starlette(routes=[Route("/rpc", rpc_handler, methods=["POST"])])


def run() -> None:
    downstream_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3001/rpc"
    signing_key = os.environ.get("MCP_GATEWAY_JWT_SIGNING_KEY")
    if not signing_key:
        print("MCP_GATEWAY_JWT_SIGNING_KEY must be configured", file=sys.stderr)
        raise SystemExit(2)

    app = create_app(downstream_url, signing_key)
    print("MCP Gateway listening on http://localhost:3000/rpc", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=3000)
