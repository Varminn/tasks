import base64
import json

import httpx
import pytest

from mcp_gateway.main import create_app


def _token(role: str) -> str:
    payload = base64.b64encode(json.dumps({"role": role}).encode()).decode()
    return f"Bearer {payload}"


def _make_request(method: str, tool_name: str | None = None, request_id: int = 1) -> dict:
    body: dict = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if tool_name is not None:
        body["params"] = {"name": tool_name, "arguments": {}}
    return body


@pytest.fixture
async def client(downstream_server):
    app = create_app(downstream_server)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestGatewayIntegration:
    @pytest.mark.anyio
    async def test_tools_list_forwards(self, client):
        response = await client.post(
            "/rpc",
            json=_make_request("tools/list"),
            headers={"Authorization": _token("viewer")},
        )
        body = response.json()
        assert "result" in body
        assert len(body["result"]["tools"]) == 2

    @pytest.mark.anyio
    async def test_tools_call_viewer_regular_tool_allowed(self, client):
        response = await client.post(
            "/rpc",
            json=_make_request("tools/call", "get_customer_record"),
            headers={"Authorization": _token("viewer")},
        )
        body = response.json()
        assert body["result"]["customer_id"] == "CUST-00001"

    @pytest.mark.anyio
    async def test_tools_call_admin_tool_with_admin_role(self, client):
        response = await client.post(
            "/rpc",
            json=_make_request("tools/call", "admin_reset_key"),
            headers={"Authorization": _token("admin")},
        )
        body = response.json()
        assert body["result"]["status"] == "key_reset"

    @pytest.mark.anyio
    async def test_tools_call_admin_tool_with_viewer_role_blocked(self, client):
        response = await client.post(
            "/rpc",
            json=_make_request("tools/call", "admin_reset_key"),
            headers={"Authorization": _token("viewer")},
        )
        body = response.json()
        assert body["error"]["code"] == -32001
        assert body["error"]["message"] == "Unauthorized Tool Call"

    @pytest.mark.anyio
    async def test_missing_auth_header_rejected(self, client):
        response = await client.post("/rpc", json=_make_request("tools/list"))
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_invalid_jsonrpc_method(self, client):
        response = await client.post(
            "/rpc",
            json={"jsonrpc": "1.0", "id": 1, "method": "tools/list"},
            headers={"Authorization": _token("admin")},
        )
        body = response.json()
        assert body["error"]["code"] == -32600

    @pytest.mark.anyio
    async def test_missing_body(self, client):
        response = await client.post(
            "/rpc",
            headers={"Authorization": _token("admin")},
        )
        assert response.status_code == 400
