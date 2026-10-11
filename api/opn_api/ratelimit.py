"""Rate limits at the identity layer (F05-R6; D-19, D-28).

Fixed windows: a counter per (scope, subject, window start) in the store, expiring with the
window. Over the limit the response is 429 with ``Retry-After`` = seconds to the window's end.
The policy in force is what ``info.json`` publishes (``Settings.rate_limit_policy``).
"""

from __future__ import annotations

from dataclasses import dataclass
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


def check_check(ctx: Context, identity_id: str) -> None:
    """F13-R8: fast checks per identity per hour."""
    enforce(ctx, "check", identity_id, limit=ctx.settings.checks_per_hour, seconds=HOUR_S)


@dataclass
class Reservation:
    """Checks taken from an identity's hourly budget before a route asks the checker anything
    (F13-T28): ``held`` were added to the window's counter at once, each pre-flight ``take``s
    one where it would have been charged, and ``release`` gives back what none of them used."""

    ctx: Context
    key: str
    expires: datetime
    held: int
    taken: int = 0

    def take(self) -> None:
        if self.taken >= self.held:
            msg = f"a pre-flight took more than the {self.held} check(s) reserved for it"
            raise RuntimeError(msg)
        self.taken += 1

    def release(self) -> None:
        unused = self.held - self.taken
        if unused > 0:
            self.ctx.store.bump_counter(self.key, self.expires, by=-unused)
            self.held = self.taken


def reserve_checks(ctx: Context, identity_id: str, n: int) -> Reservation:
    """F13-T28 (the owner's ruling amending F13-Q22): ``n`` fast checks from the identity's hourly
    budget, all or none. One atomic add; over the limit it is taken back at once and the caller
    gets the 429 ``check_check`` would give, with ``Retry-After``, before anything is asked or
    opened. The same counter as ``check_check``, so ``POST /check`` and the pre-flights share
    one budget (R8)."""
    from opn_api.app import ApiError  # noqa: PLC0415 — app imports this module

    now = ctx.clock.now()
    start, ends = window(now, HOUR_S)
    key = f"{KEY_RATE}check#{identity_id}#{start}"
    if n <= 0:
        return Reservation(ctx, key, ends, 0)
    limit = ctx.settings.checks_per_hour
    count = ctx.store.bump_counter(key, ends, by=n)
    if count > limit:
        ctx.store.bump_counter(key, ends, by=-n)
        raise ApiError(
            429,
            "rate-limited",
            f"check: limit of {limit} per {HOUR_S}s reached ({n} needed by this request's "
            "pre-flights; nothing was asked and nothing opened)",
            headers={"Retry-After": retry_after(now, ends)},
        )
    return Reservation(ctx, key, ends, n)


def check_anonymous_check(ctx: Context, address: str) -> None:
    """F13-R8, Q2: anonymous fast checks per source address per day."""
    enforce(ctx, "anon-check", address, limit=ctx.settings.anonymous_checks_per_day, seconds=DAY_S)


def client_address(request: Request) -> str:
    """The source address: the ASGI peer, never a header (F05-T19).

    On Lambda, Mangum fills the peer from the HTTP API event's ``requestContext.http.sourceIp``,
    which API Gateway sets and the caller cannot. ``X-Forwarded-For`` is not read at all: API
    Gateway appends the real address to whatever the caller sent, so the header's first hop is
    the caller's to write, and keying a limit on it made every per-source limit unlimited."""
    return request.client.host if request.client else "unknown"


def retry_after(now: datetime, when: datetime) -> str:
    return str(max(1, int((when - now).total_seconds())))
