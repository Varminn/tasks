import base64
import binascii
import hashlib
import hmac
import json
import time

from pydantic import BaseModel


class TokenClaims(BaseModel):
    role: str


def parse_bearer_token(header_value: str, signing_key: str) -> TokenClaims:
    """Verify an HS256 Bearer JWT and return its role claim."""
    scheme, separator, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not separator:
        raise ValueError("Authorization header must use Bearer scheme")

    token = token.strip()
    if not token:
        raise ValueError("Bearer token is empty")
    if not signing_key:
        raise ValueError("JWT signing key is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Bearer token must be a compact JWT")

    header_segment, payload_segment, signature_segment = parts
    header = _decode_json_segment(header_segment, "JWT header")
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise ValueError("JWT must use HS256")

    expected_signature = hmac.new(
        signing_key.encode(),
        f"{header_segment}.{payload_segment}".encode(),
        hashlib.sha256,
    ).digest()
    supplied_signature = _decode_base64url(signature_segment, "JWT signature")
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise ValueError("JWT signature is invalid")

    claims = _decode_json_segment(payload_segment, "JWT payload")
    return _extract_role(claims)


def _decode_json_segment(segment: str, label: str) -> object:
    try:
        decoded = _decode_base64url(segment, label)
        return json.loads(decoded)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid {label}") from exc


def _decode_base64url(segment: str, label: str) -> bytes:
    try:
        return base64.b64decode(
            segment + "=" * (-len(segment) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid {label}") from exc


def _extract_role(claims: object) -> TokenClaims:
    if not isinstance(claims, dict):
        raise ValueError("Token payload must be a JSON object")

    role = claims.get("role")
    if not isinstance(role, str) or not role:
        raise ValueError("Token must contain a non-empty 'role' claim")

    expires_at = claims.get("exp")
    if not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool):
        raise ValueError("Token must contain a numeric 'exp' claim")
    if expires_at <= time.time():
        raise ValueError("Token has expired")

    return TokenClaims(role=role)
