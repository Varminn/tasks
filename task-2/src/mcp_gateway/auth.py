import base64
import binascii
import json

from pydantic import BaseModel


class TokenClaims(BaseModel):
    role: str


def parse_bearer_token(header_value: str) -> TokenClaims:
    """Parse a Bearer token and extract the role claim.

    Supports JWT (three base64url segments) and simple base64-encoded JSON
    tokens of the form {"role": "..."}.
    """
    if not header_value.startswith("Bearer "):
        raise ValueError("Authorization header must use Bearer scheme")

    token = header_value.removeprefix("Bearer ").strip()
    if not token:
        raise ValueError("Bearer token is empty")

    parts = token.split(".")
    if len(parts) == 3:
        return _parse_jwt_payload(parts[1])

    return _parse_simple_token(token)


def _parse_jwt_payload(payload_segment: str) -> TokenClaims:
    try:
        decoded = base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4))
        claims = json.loads(decoded)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid JWT payload: {exc}") from exc

    return _extract_role(claims)


def _parse_simple_token(token: str) -> TokenClaims:
    try:
        decoded = base64.b64decode(token)
        claims = json.loads(decoded)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid token encoding: {exc}") from exc

    return _extract_role(claims)


def _extract_role(claims: object) -> TokenClaims:
    if not isinstance(claims, dict):
        raise ValueError("Token payload must be a JSON object")

    role = claims.get("role")
    if not isinstance(role, str) or not role:
        raise ValueError("Token must contain a non-empty 'role' claim")

    return TokenClaims(role=role)
