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
from typing import TYPE_CHECKING, Any

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


# --- web sessions (F23-R3; D-35 v3.33) -----------------------------------------------------------

#: The cookie a web session rides in, on the service's own host.
SESSION_COOKIE = "opn_session"
#: The header the site's script adds to every credentialed call: a form on another site cannot
#: set it, and a cross-origin script cannot either without a preflight only the site passes.
WEB_HEADER = "x-opn-web"
KEY_WEB_SESSION = "websession#"


def session_key(settings: Settings, raw: str) -> str:
    """Where a session is kept: its id is hashed as a token is (R4), so a copied table names no
    live session."""
    return KEY_WEB_SESSION + token_hash(settings.token_secret or "", raw)


def new_session(ctx: Context, identity_id: str) -> tuple[str, datetime]:
    """A fresh web session for ``identity_id``: the raw id (for the cookie, shown nowhere else)
    and when it ends (``web_session_ttl_s``, eight hours by default)."""
    raw = new_token()
    now = ctx.clock.now()
    ends = now + timedelta(seconds=ctx.settings.web_session_ttl_s)
    ctx.store.put_ephemeral(
        session_key(ctx.settings, raw),
        {"identity_id": identity_id, "created": clock.render(now), "expires": clock.render(ends)},
        ends,
    )
    return raw, ends


def session_cookie(raw: str, max_age: int) -> str:
    """The ``Set-Cookie`` value: HttpOnly so no script on the site can read it, Secure, and
    SameSite=Strict so no other site's page can send it (F23 §7)."""
    return f"{SESSION_COOKIE}={raw}; Max-Age={max_age}; Path=/; HttpOnly; Secure; SameSite=Strict"


def session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE) or None


def web_request(ctx: Context, request: Request) -> bool:
    """R3: the request comes from the site's own page — its ``Origin`` is exactly the configured
    site origin and it carries ``X-OPN-Web: 1``. Anything else never reads the cookie."""
    origin = ctx.settings.site_origin
    return (
        bool(origin)
        and request.headers.get("origin") == origin
        and request.headers.get(WEB_HEADER) == "1"
    )


def web_session(ctx: Context, request: Request) -> tuple[dict[str, Any], Identity] | None:
    """The live session record and its identity behind the cookie, on a web request only;
    ``None`` for no cookie, an unknown or ended session, or a request that is not the site's."""
    raw = session_id(request)
    if raw is None or not web_request(ctx, request):
        return None
    record = ctx.store.get_ephemeral(session_key(ctx.settings, raw), ctx.clock.now())
    if record is None:
        return None
    identity = ctx.store.get_identity(str(record.get("identity_id", "")))
    if identity is None:
        return None
    return record, identity


def end_session(ctx: Context, request: Request) -> None:
    raw = session_id(request)
    if raw is not None:
        ctx.store.drop_ephemeral(session_key(ctx.settings, raw))


def authenticate_web(ctx: Context, request: Request) -> Identity:
    """F23-R3: the one resolver of the routes that accept a web session. A bearer, when
    presented, is authenticated exactly as everywhere else; without one, the web session is the
    identity; with neither, the 401 every authenticated route gives."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    if bearer(request) is not None:
        return authenticate(ctx, request)
    found = web_session(ctx, request)
    if found is None:
        raise ApiError(
            401,
            "unauthenticated",
            "this route needs `Authorization: Bearer <token>`, or a web session from the site",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return found[1]


def cors_headers(ctx: Context) -> dict[str, str]:
    """F23-Q2: the credentialed CORS answer, for the site's one origin and nobody else's."""
    origin = ctx.settings.site_origin
    if not origin:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


#: What a preflight allows (F23-R3): the site's script sends JSON and the marker header.
PREFLIGHT_HEADERS = "Content-Type, X-OPN-Web"
PREFLIGHT_MAX_AGE_S = 600
