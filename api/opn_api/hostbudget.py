"""The App's host budget as the service reasons about it (F07-T47; C7).

GitHub puts ``X-RateLimit-Remaining``, ``-Limit`` and ``-Reset`` on every API answer and the
``GitHost`` seam keeps the latest reading (``githost.HostBudget``). Three questions are asked of
it here, all against the service's clock as unix seconds:

- ``exhausted``: the budget is spent (nothing remaining) and the reset is still ahead, so the
  host will refuse every call until then. ``/health`` goes red on it.
- ``held``: the budget is at or below the reserve kept for writes and the reset is ahead, so an
  unauthenticated read must not spend it; the read serves what it has as stale. Spent implies
  held.
- ``retry_after_s``: seconds until the reset, for a ``Retry-After`` header.

Pure functions: no seam, no request, nothing raised.
"""

from __future__ import annotations

import math
from typing import Any

from opn_api.githost import HostBudget


def exhausted(budget: HostBudget, now: float) -> bool:
    return budget.remaining == 0 and _reset_ahead(budget, now)


def held(budget: HostBudget, now: float, reserve: int) -> bool:
    return (
        budget.remaining is not None and budget.remaining <= reserve and _reset_ahead(budget, now)
    )


def _reset_ahead(budget: HostBudget, now: float) -> bool:
    return budget.reset_at is not None and budget.reset_at > now


def retry_after_s(budget: HostBudget, now: float) -> int:
    """Seconds until the budget refills, at least one; one minute when the host named no reset
    (it always does, but a header is never a fact until read)."""
    if budget.reset_at is None:
        return 60
    return max(1, math.ceil(budget.reset_at - now))


def describe(budget: HostBudget | None) -> dict[str, Any] | None:
    """The budget as ``/health`` reports it, or ``None`` when nothing has been read."""
    if budget is None:
        return None
    return {
        "remaining": budget.remaining,
        "limit": budget.limit,
        "reset_at": budget.reset_iso,
        "read_at": _iso(budget.read_at),
    }


def _iso(seconds: float) -> str:
    return HostBudget(None, None, seconds, seconds).reset_iso or ""


def _refills(budget: HostBudget, now: float) -> str:
    when = budget.reset_iso or "an unknown time"
    return f"it refills at {when} (in {retry_after_s(budget, now)} s)"


def refusal_message(budget: HostBudget, now: float) -> str:
    """What a route that needed the host to act says when the host refused for budget."""
    limit = f" of {budget.limit}" if budget.limit is not None else ""
    return (
        f"the service's GitHub budget is spent (0{limit} calls left this hour); "
        f"{_refills(budget, now)}; retry then"
    )


def read_message(budget: HostBudget, now: float, reserve: int) -> str:
    """Why a read served its cached state instead of asking the host: the budget is spent, or
    down to the reserve kept for the writes. Prefixed with the error code, since a read's error
    is a string field, not a status."""
    limit = f" of {budget.limit}" if budget.limit is not None else ""
    if budget.remaining == 0:
        why = f"the service's GitHub budget is spent (0{limit} calls left this hour)"
    else:
        why = (
            f"the service's GitHub budget is down to its reserve ({budget.remaining}{limit} "
            f"calls left this hour, {reserve} kept for writes)"
        )
    return f"host-budget-exhausted: {why}; {_refills(budget, now)}"
