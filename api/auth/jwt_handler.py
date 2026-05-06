"""JWT encode / decode — S9-01.

Validates Bearer tokens issued by Auth0, Clerk, or the local dev-token endpoint.
Algorithm: HS256 (shared secret) in dev; RS256 (JWKS) in production.

Environment variables:
    JWT_SECRET          HS256 secret (dev / staging)
    JWT_ALGORITHM       HS256 (default) | RS256
    JWT_ISSUER          Expected `iss` claim (optional, for extra validation)
    JWT_AUDIENCE        Expected `aud` claim (optional)
    JWT_EXPIRY_SECONDS  Dev-token TTL in seconds (default: 3600)
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

_SECRET    = os.getenv("JWT_SECRET", "dev-insecure-secret-change-in-production")
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_ISSUER    = os.getenv("JWT_ISSUER")
_AUDIENCE  = os.getenv("JWT_AUDIENCE")
_EXPIRY    = int(os.getenv("JWT_EXPIRY_SECONDS", "3600"))

# Default org for development / backward-compatibility
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Token claims ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TokenClaims:
    """Decoded, validated JWT claims attached to each authenticated request."""

    sub:    str                        # external user ID
    email:  str
    org_id: uuid.UUID
    role:   str                        # admin | marketer | analyst | viewer
    extra:  dict[str, object] = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


# Guest used when AUTH_REQUIRED is disabled
GUEST_CLAIMS = TokenClaims(
    sub="dev-guest",
    email="dev@localhost",
    org_id=DEFAULT_ORG_ID,
    role="admin",
)


# ── Encode (dev-token endpoint only) ─────────────────────────────────────────

def encode_token(
    sub: str,
    email: str,
    org_id: uuid.UUID,
    role: str,
    expiry_seconds: int = _EXPIRY,
) -> str:
    """Encode a JWT with the configured HS256 secret. Dev use only."""
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, object] = {
        "sub":    sub,
        "email":  email,
        "org_id": str(org_id),
        "role":   role,
        "iat":    now,
        "exp":    now + timedelta(seconds=expiry_seconds),
    }
    if _ISSUER:
        payload["iss"] = _ISSUER
    if _AUDIENCE:
        payload["aud"] = _AUDIENCE
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)  # type: ignore[return-value]


# ── Decode ────────────────────────────────────────────────────────────────────

def decode_token(raw_token: str) -> TokenClaims:
    """Verify and decode a JWT.  Raises ``InvalidTokenError`` on failure."""
    options: dict[str, object] = {}
    if not _ISSUER:
        options["verify_iss"] = False
    if not _AUDIENCE:
        options["verify_aud"] = False

    try:
        payload = jwt.decode(
            raw_token,
            _SECRET,
            algorithms=[_ALGORITHM],
            issuer=_ISSUER or None,
            audience=_AUDIENCE or None,
            options=options,
        )
    except InvalidTokenError:
        raise

    org_id_raw = payload.get("org_id", str(DEFAULT_ORG_ID))
    try:
        org_id = uuid.UUID(str(org_id_raw))
    except ValueError:
        org_id = DEFAULT_ORG_ID

    return TokenClaims(
        sub=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        org_id=org_id,
        role=str(payload.get("role", "viewer")),
    )
