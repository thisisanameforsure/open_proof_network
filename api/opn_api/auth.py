"""Tokens and bearer authentication (F05-R4, R5).

A token is 32 random bytes, base64url without padding (§6), shown once. The store holds only
``HMAC-SHA256(token_secret, token)`` — a salted hash keyed by the service's secret (C8 item 3),
so a copied table yields nothing without the parameter. Resolution hashes the presented token
and looks the hash up: the work is the same for a known and an unknown token (R5).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING

from starlette.requests import Request

from opn_api.store import Identity

if TYPE_CHECKING:
    from opn_api.app import Context

TOKEN_BYTES = 32
SCHEME = "Bearer "


def new_token() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(TOKEN_BYTES)).decode().rstrip("=")


def token_hash(secret: str, token: str) -> str:
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.startswith(SCHEME):
        return None
    return header[len(SCHEME) :].strip() or None


def authenticate(ctx: Context, request: Request) -> Identity:
    """The identity behind ``Authorization: Bearer``, or a 401 (R5; AC6)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    token = bearer(request)
    if token is None:
        raise ApiError(
            401,
            "unauthenticated",
            "this route needs `Authorization: Bearer <token>`",
            headers={"WWW-Authenticate": "Bearer"},
        )
    digest = token_hash(ctx.settings.token_secret or "", token)
    record = ctx.store.get_token(digest)
    known = record is not None and hmac.compare_digest(record.token_hash, digest)
    identity = ctx.store.get_identity(record.identity_id) if known and record else None
    if not known or (record is not None and record.revoked) or identity is None:
        raise ApiError(
            401, "invalid-token", "unknown or revoked token", headers={"WWW-Authenticate": "Bearer"}
        )
    return identity
