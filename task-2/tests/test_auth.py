import base64
import hashlib
import hmac
import json
import time

import pytest

from mcp_gateway.auth import parse_bearer_token

JWT_SIGNING_KEY = "test-signing-key"


def _make_jwt(claims: dict, signing_key: str = JWT_SIGNING_KEY) -> str:
    claims = {"exp": time.time() + 60, **claims}
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    signed_content = f"{header.decode()}.{payload.decode()}"
    signature = hmac.new(signing_key.encode(), signed_content.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{signed_content}.{encoded_signature.decode()}"


class TestParseBearerToken:
    def test_valid_jwt_admin(self):
        token = _make_jwt({"role": "admin", "sub": "123"})
        claims = parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)
        assert claims.role == "admin"

    def test_valid_jwt_viewer(self):
        token = _make_jwt({"role": "viewer"})
        claims = parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)
        assert claims.role == "viewer"

    def test_missing_bearer_prefix(self):
        with pytest.raises(ValueError, match="Bearer"):
            parse_bearer_token("some-token", JWT_SIGNING_KEY)

    def test_empty_token(self):
        with pytest.raises(ValueError, match="empty"):
            parse_bearer_token("Bearer ", JWT_SIGNING_KEY)

    def test_invalid_jwt_signature(self):
        token = _make_jwt({"role": "admin"}, signing_key="wrong-key")
        with pytest.raises(ValueError, match="signature"):
            parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)

    def test_missing_role_claim(self):
        token = _make_jwt({"sub": "123"})
        with pytest.raises(ValueError, match="role"):
            parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)

    def test_expired_token_rejected(self):
        token = _make_jwt({"role": "viewer", "exp": time.time() - 1})
        with pytest.raises(ValueError, match="expired"):
            parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)

    def test_missing_expiration_rejected(self):
        claims = {"role": "viewer"}
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
        signed_content = f"{header.decode()}.{payload.decode()}"
        signature = hmac.new(JWT_SIGNING_KEY.encode(), signed_content.encode(), hashlib.sha256).digest()
        token = f"{signed_content}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"
        with pytest.raises(ValueError, match="exp"):
            parse_bearer_token(f"Bearer {token}", JWT_SIGNING_KEY)
