import httpx

from mcp_gateway.authz import (
    UNAUTHORIZED_ERROR_CODE,
    UNAUTHORIZED_ERROR_MESSAGE,
    is_tool_authorized,
)
from mcp_gateway.models import JsonRpcRequest, jsonrpc_error


class McpProxy:
    """Forwards JSON-RPC requests to a downstream MCP server with auth checks."""

    def __init__(self, downstream_url: str) -> None:
        self._downstream_url = downstream_url.rstrip("/")

    async def handle(self, request: JsonRpcRequest, role: str) -> dict:
        if request.method == "tools/call":
            tool_name = request.get_tool_name()
            if not tool_name:
                return jsonrpc_error(request.id, -32602, "Invalid params: tools/call requires params.name")
            if not is_tool_authorized(tool_name, role):
                return jsonrpc_error(
                    request.id,
                    UNAUTHORIZED_ERROR_CODE,
                    UNAUTHORIZED_ERROR_MESSAGE,
                )

        return await self._forward(request)

    async def _forward(self, request: JsonRpcRequest) -> dict:
        payload = request.model_dump(exclude_unset=True)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self._downstream_url, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                return jsonrpc_error(
                    request.id,
                    -32603,
                    f"Downstream error: {exc.response.status_code}",
                )
            except httpx.RequestError:
                return jsonrpc_error(request.id, -32603, "Downstream server unreachable")
            except ValueError:
                return jsonrpc_error(request.id, -32603, "Downstream returned invalid JSON")
