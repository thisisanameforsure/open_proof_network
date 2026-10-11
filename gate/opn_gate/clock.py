"""The gate's clock (F24-R10; D-32 v3.34).

The gate has one notion of "today": the UTC date this function returns. A record that carries a
date the gate must judge (a motion, a vote, a write-up act) is held to within one day of it, so
nobody can write a vote into a closed window. Nothing else in the gate reads the wall clock for
a date; tests replace this function (``monkeypatch.setattr(clock, "today", ...)``).
"""

from __future__ import annotations

import datetime as dt

#: How far a record's own date may stand from the gate's day (F24-R10).
TOLERANCE = dt.timedelta(days=1)


def today() -> dt.date:
    """The gate's day, in UTC."""
    return dt.datetime.now(dt.UTC).date()


def near(day: dt.date) -> bool:
    """Whether ``day`` is within one day of the gate's own (F24-R10)."""
    return abs(day - today()) <= TOLERANCE
