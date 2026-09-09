"""The ``Clock`` seam (conventions §1): every "now" the api uses comes from here.

Times are timezone-aware UTC ``datetime`` values; records store them as ISO 8601 strings with
second precision and a ``Z`` suffix (the protocol's timestamp shape, D-34).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC).replace(microsecond=0)


def render(when: datetime) -> str:
    """``2026-09-09T06:00:00Z`` — the one timestamp serialization records carry."""
    return when.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def parse(text: str) -> datetime:
    return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
