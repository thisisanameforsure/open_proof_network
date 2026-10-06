"""Tokens and bearer authentication (F05-R4, R5).

A token is 32 random bytes, base64url without padding (§6), shown once. The store holds only
``HMAC-SHA256(token_secret, token)`` — a salted hash keyed by the service's secret (C8 item 3),
so a copied table yields nothing without the parameter. Resolution hashes the presented token
and looks the hash up: the work is the same for a known and an unknown token (R5).

D-19 v3.29 (F05-T29): a token lapses only after ``OPN_API_TOKEN_IDLE_DAYS`` without use, so a
token in use never lapses and nothing has to be renewed (an agent keeps no memory between
sessions). Each authenticated use refreshes ``last_used``, written at most once a day. A lapsed
token is ``401 token-expired``; rotation (``POST /tokens/renew``, F05-T27) stays, never required.
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


#: How stale ``last_used`` may be before a use writes it again (F05-T29): one write a day.
TOUCH_EVERY = timedelta(days=1)


def idle_since(settings: Settings, record: TokenRecord) -> datetime:
    """When ``record``'s disuse began (D-19 v3.29, F05-T29): its last recorded use (issue counts as
    one). A token issued before uses were recorded has none, and counts from the later of its
    issue and ``OPN_API_TOKEN_CUTOVER``, so a token held at the deploy gets a full window from it
    rather than lapsing at once (Q29)."""
    if record.last_used:
        return clock.parse(record.last_used)
    cutover = datetime.fromisoformat(settings.token_cutover).replace(tzinfo=UTC)
    return max(clock.parse(record.created), cutover)


def expiry(settings: Settings, record: TokenRecord) -> datetime:
    """When ``record`` lapses if it is not used before then."""
    return idle_since(settings, record) + timedelta(days=settings.token_idle_days)


def lapsed(ctx: Context, record: TokenRecord) -> bool:
    return ctx.clock.now() >= expiry(ctx.settings, record)


def lapsed_message(ctx: Context, record: TokenRecord) -> str:
    since = clock.render(idle_since(ctx.settings, record))
    days = ctx.settings.token_idle_days
    return (
        f"this token lapsed after {days} days without use (unused since {since}); a token in use "
        "never lapses. The identity is kept: a GitHub identity proves the same login again "
        "(GET /auth/github/start, then POST /tokens with the same pseudonym) for a new token. A "
        "tutorial identity has no second proof, and the recovery code of D-19 v3.29 is not built "
        "yet (F05-T30): keep its token where the machine remembers it"
    )


def touch(ctx: Context, record: TokenRecord) -> None:
    """Record this use, at most once a day per token (F05-T29): a conditional write, so a busy
    agent costs one store write a day, never one a request, even when requests race."""
    now = ctx.clock.now()
    if record.last_used and now - clock.parse(record.last_used) < TOUCH_EVERY:
        return
    ctx.store.touch_token(record.token_hash, clock.render(now), clock.render(now - TOUCH_EVERY))


def resolve(ctx: Context, token: str) -> tuple[TokenRecord, Identity]:
    """The record and identity behind ``token``, or the 401 that refuses it (R5; D-19 v3.29).

    Unknown, revoked and renewed tokens are ``invalid-token``; a known token unused for the idle
    window is ``token-expired``. A token that resolves has this use recorded (``touch``). A
    renewed token's message says so, so a holder who did not renew learns that someone holding
    their token did."""
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
    touch(ctx, record)
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
