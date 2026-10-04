"""Tokens and bearer authentication (F05-R4, R5).

A token is 32 random bytes, base64url without padding (§6), shown once. The store holds only
``HMAC-SHA256(token_secret, token)`` — a salted hash keyed by the service's secret (C8 item 3),
so a copied table yields nothing without the parameter. Resolution hashes the presented token
and looks the hash up: the work is the same for a known and an unknown token (R5).

D-19 v3.28 (F05-T27): a token is valid ``OPN_API_TOKEN_DAYS`` from its issue or its last
renewal. A lapsed one is ``401 token-expired``; renewal (``POST /tokens/renew``) rotates it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from starlette.requests import Request

from opn_api import clock
from opn_api.store import Identity, TokenRecord

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.config import Settings

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


def expiry(settings: Settings, record: TokenRecord) -> datetime:
    """When ``record`` lapses (D-19 v3.28, F05-T27): its own ``expires``, or — for a token issued
    before tokens carried one — ``OPN_API_TOKEN_CUTOVER`` plus the window, so a token that was
    live at the deploy gets a full window from it rather than lapsing at once (Q27)."""
    if record.expires:
        return clock.parse(record.expires)
    cutover = datetime.fromisoformat(settings.token_cutover).replace(tzinfo=UTC)
    return cutover + timedelta(days=settings.token_days)


def new_expiry(settings: Settings, now: datetime) -> str:
    """The ``expires`` of a token issued or renewed at ``now``."""
    return clock.render(now + timedelta(days=settings.token_days))


def lapsed(ctx: Context, record: TokenRecord) -> bool:
    return ctx.clock.now() >= expiry(ctx.settings, record)


def lapsed_message(ctx: Context, record: TokenRecord) -> str:
    when = clock.render(expiry(ctx.settings, record))
    return (
        f"this token lapsed at {when}: a token is valid {ctx.settings.token_days} days from its "
        "issue or its last renewal, and is renewed before then with POST /tokens/renew (the "
        "renew_token tool). The identity is kept: a GitHub identity gets a new token for the "
        "same pseudonym by proving the same login again (GET /auth/github/start, then POST "
        "/tokens with the same pseudonym)"
    )


def resolve(ctx: Context, token: str) -> tuple[TokenRecord, Identity]:
    """The record and identity behind ``token``, or the 401 that refuses it (R5; D-19 v3.28).

    Unknown, revoked and renewed tokens are ``invalid-token``; a known token past its window is
    ``token-expired``. A renewed token's message says so, so a holder who did not renew learns
    that someone holding their token did."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    challenge = {"WWW-Authenticate": "Bearer"}
    digest = token_hash(ctx.settings.token_secret or "", token)
    record = ctx.store.get_token(digest)
    known = record is not None and hmac.compare_digest(record.token_hash, digest)
    identity = ctx.store.get_identity(record.identity_id) if known and record else None
    if record is None or not known or identity is None:
        raise ApiError(401, "invalid-token", "unknown or revoked token", headers=challenge)
    if record.renewed:
        raise ApiError(
            401,
            "invalid-token",
            f"this token was replaced by a renewal at {record.renewed}; use the token that "
            "renewal returned. If you did not renew it, someone holding this token did: ask the "
            "operator to revoke the identity's tokens",
            headers=challenge,
        )
    if record.revoked:
        raise ApiError(401, "invalid-token", "unknown or revoked token", headers=challenge)
    if lapsed(ctx, record):
        raise ApiError(
            401,
            "token-expired",
            lapsed_message(ctx, record),
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    return record, identity


def authenticate(ctx: Context, request: Request) -> Identity:
    """The identity behind ``Authorization: Bearer``, or a 401 (R5; AC6)."""
    return authenticated(ctx, request)[1]


def authenticated(ctx: Context, request: Request) -> tuple[TokenRecord, Identity]:
    """``authenticate`` with the token's record, which renewal retires (F05-T27)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    token = bearer(request)
    if token is None:
        raise ApiError(
            401,
            "unauthenticated",
            "this route needs `Authorization: Bearer <token>`",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return resolve(ctx, token)
