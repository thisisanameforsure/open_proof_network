"""Rate limits at the identity layer (F05-R6; D-19, D-28).

Fixed windows: a counter per (scope, subject, window start) in the store, expiring with the
window. Over the limit the response is 429 with ``Retry-After`` = seconds to the window's end.
The policy in force is what ``info.json`` publishes (``Settings.rate_limit_policy``).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from starlette.requests import Request

from opn_api.store import KEY_RATE

if TYPE_CHECKING:
    from opn_api.app import Context

HOUR_S = 3600
DAY_S = 86400


def window(now: datetime, seconds: int) -> tuple[int, datetime]:
    """(window start as epoch seconds, window end) for the fixed window containing ``now``."""
    epoch = int(now.timestamp())
    start = epoch - epoch % seconds
    return start, datetime.fromtimestamp(start + seconds, tz=now.tzinfo)


def enforce(ctx: Context, scope: str, subject: str, *, limit: int, seconds: int) -> None:
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    now = ctx.clock.now()
    start, ends = window(now, seconds)
    count = ctx.store.bump_counter(f"{KEY_RATE}{scope}#{subject}#{start}", ends)
    if count > limit:
        retry = max(1, int((ends - now).total_seconds()))
        raise ApiError(
            429,
            "rate-limited",
            f"{scope}: limit of {limit} per {seconds}s reached",
            headers={"Retry-After": str(retry)},
        )


def check_write(ctx: Context, identity_id: str) -> None:
    """R6: writes per identity per hour (AC7)."""
    enforce(ctx, "write", identity_id, limit=ctx.settings.writes_per_hour, seconds=HOUR_S)


def check_token_start(ctx: Context, address: str) -> None:
    """R6: token starts per source address per day."""
    enforce(ctx, "start", address, limit=ctx.settings.token_starts_per_day, seconds=DAY_S)


def check_precheck(ctx: Context, identity_id: str) -> None:
    """F06-R8: authenticated prechecks per identity per hour."""
    enforce(ctx, "precheck", identity_id, limit=ctx.settings.prechecks_per_hour, seconds=HOUR_S)


def check_anonymous_precheck(ctx: Context, address: str) -> None:
    """F06-R2: anonymous tutorial prechecks per source address per day (the one unauthenticated
    write-shaped route, so the address limit is what bounds it)."""
    enforce(
        ctx, "anon-precheck", address, limit=ctx.settings.anonymous_prechecks_per_day, seconds=DAY_S
    )


def check_proposal(ctx: Context, identity_id: str) -> None:
    """F08 §6, D-29: node proposals per identity per day — the identity-layer bound on graph
    spam, never a review (F08 §7)."""
    enforce(ctx, "proposal", identity_id, limit=ctx.settings.proposals_per_day, seconds=DAY_S)


def client_address(request: Request) -> str:
    """The source address: the first ``X-Forwarded-For`` hop (API Gateway sets it) or the peer."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def retry_after(now: datetime, when: datetime) -> str:
    return str(max(1, int((when - now).total_seconds())))
