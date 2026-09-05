import base64
import json

import pytest

from mcp_gateway.auth import parse_bearer_token


def _make_jwt(claims: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.signature"


class TestParseBearerToken:
    def test_valid_jwt_admin(self):
        token = _make_jwt({"role": "admin", "sub": "123"})
        claims = parse_bearer_token(f"Bearer {token}")
        assert claims.role == "admin"

    def test_valid_jwt_viewer(self):
        token = _make_jwt({"role": "viewer"})
        claims = parse_bearer_token(f"Bearer {token}")
        assert claims.role == "viewer"

    def test_missing_bearer_prefix(self):
        with pytest.raises(ValueError, match="Bearer"):
            parse_bearer_token("some-token")

    def test_empty_token(self):
        with pytest.raises(ValueError, match="empty"):
            parse_bearer_token("Bearer ")

    def test_invalid_jwt_payload(self):
        with pytest.raises(ValueError, match="Invalid JWT"):
            parse_bearer_token("Bearer aaa.bbb.ccc")

    def test_missing_role_claim(self):
        token = _make_jwt({"sub": "123"})
        with pytest.raises(ValueError, match="role"):
            parse_bearer_token(f"Bearer {token}")

    def test_non_dict_payload(self):
        payload = base64.urlsafe_b64encode(json.dumps("string").encode()).rstrip(b"=")
        token = f"header.{payload.decode()}.sig"
        with pytest.raises(ValueError, match="JSON object"):
            parse_bearer_token(f"Bearer {token}")
