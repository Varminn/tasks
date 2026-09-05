import json
import sys

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp_gateway.auth import parse_bearer_token
from mcp_gateway.models import JsonRpcRequest
from mcp_gateway.proxy import McpProxy


def create_app(downstream_url: str = "http://localhost:3001/rpc") -> Starlette:
    proxy = McpProxy(downstream_url)

    async def rpc_handler(request: Request) -> JSONResponse:
        auth_header = request.headers.get("authorization", "")
        try:
            claims = parse_bearer_token(auth_header)
        except ValueError as exc:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32001, "message": str(exc)},
                },
                status_code=401,
            )

        try:
            body = await request.json()
            rpc_request = JsonRpcRequest.model_validate(body)
        except Exception:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
                },
                status_code=400,
            )

        result = await proxy.handle(rpc_request, claims.role)
        return JSONResponse(result)

    return Starlette(routes=[Route("/rpc", rpc_handler, methods=["POST"])])


def run() -> None:
    downstream_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3001/rpc"
    app = create_app(downstream_url)
    print("MCP Gateway listening on http://localhost:3000/rpc", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=3000)
