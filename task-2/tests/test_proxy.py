import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest

from mcp_gateway.main import create_app

JWT_SIGNING_KEY = "test-signing-key"


def _token(role: str) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": role, "exp": time.time() + 60}).encode()
    ).rstrip(b"=")
    signed_content = f"{header.decode()}.{payload.decode()}"
    signature = hmac.new(JWT_SIGNING_KEY.encode(), signed_content.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"Bearer {signed_content}.{encoded_signature.decode()}"


def _make_request(method: str, tool_name: str | None = None, request_id: int = 1) -> dict:
    body: dict = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if tool_name is not None:
        body["params"] = {"name": tool_name, "arguments": {}}
    return body


@pytest.fixture
async def client(downstream_server):
    app = create_app(downstream_server, JWT_SIGNING_KEY)
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
        assert "result" not in body

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

    @pytest.mark.anyio
    async def test_tools_call_requires_a_tool_name(self, client):
        response = await client.post(
            "/rpc",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {}},
            headers={"Authorization": _token("viewer")},
        )
        body = response.json()
        assert body["error"]["code"] == -32602
        assert "result" not in body

    @pytest.mark.anyio
    async def test_invalid_downstream_json_is_sanitized(self, client):
        response = await client.post(
            "/rpc",
            json=_make_request("invalid/json"),
            headers={"Authorization": _token("viewer")},
        )
        body = response.json()
        assert body == {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Downstream returned invalid JSON"},
        }
