import httpx

from mcp_gateway.authz import (
    UNAUTHORIZED_ERROR_CODE,
    UNAUTHORIZED_ERROR_MESSAGE,
    is_tool_authorized,
)
from mcp_gateway.models import JsonRpcRequest, JsonRpcResponse


class McpProxy:
    """Forwards JSON-RPC requests to a downstream MCP server with auth checks."""

    def __init__(self, downstream_url: str) -> None:
        self._downstream_url = downstream_url.rstrip("/")

    async def handle(self, request: JsonRpcRequest, role: str) -> dict:
        if request.method == "tools/call":
            tool_name = request.get_tool_name()
            if tool_name is not None and not is_tool_authorized(tool_name, role):
                return JsonRpcResponse(
                    id=request.id,
                    error={
                        "code": UNAUTHORIZED_ERROR_CODE,
                        "message": UNAUTHORIZED_ERROR_MESSAGE,
                    },
                ).model_dump()

        return await self._forward(request)

    async def _forward(self, request: JsonRpcRequest) -> dict:
        payload = {
            "jsonrpc": request.jsonrpc,
            "method": request.method,
            "params": request.params,
        }
        if request.id is not None:
            payload["id"] = request.id

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self._downstream_url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                return JsonRpcResponse(
                    id=request.id,
                    error={"code": -32603, "message": f"Downstream error: {exc.response.status_code}"},
                ).model_dump()
            except httpx.RequestError:
                return JsonRpcResponse(
                    id=request.id,
                    error={"code": -32603, "message": "Downstream server unreachable"},
                ).model_dump()
