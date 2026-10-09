"""Testers 2026-10-09b (C4): ``get_my_submissions`` answered ``waiting_on: null`` for both of an
agent's pull requests in their first minute, and ``get_submission`` a minute later said ``gate``.
The queue block served what the service last read of the pull request, and never a read of its
own (``last_read``), so a pull request nobody had asked about by id had nothing to say.

A caller's own open submissions are few, so ``mine`` reads the live state of each one the service
has never read (once: the read is cached for the window) and the block says ``gate`` with the
time it was read, as the by-id route does. ``GET /submissions.json``, which lists everyone's,
still reads nothing of its own.
"""

from __future__ import annotations

from typing import Any

from api_fakes import Harness
from test_finding_submissions_mine import h, mine_doc  # noqa: F401 — the fixture, by name
from test_pending_submissions import annex


def entry(doc: dict[str, Any], submission_id: str) -> dict[str, Any]:
    found: dict[str, Any] = next(e for e in doc["open"] if e["id"] == submission_id)
    return found


def test_mine_says_what_a_never_read_submission_waits_on(h: Harness) -> None:  # noqa: F811
    alice = h.token_for("code_alice", "alice-p")
    opened = annex(h, alice)
    block = entry(mine_doc(h, alice), opened["id"])["queue"]
    assert block["waiting_on"] == "gate", block
    assert block["waiting_on_read_at"] is not None, block
    # the read is the window's, as the by-id route's: a second listing reads nothing more
    again = entry(mine_doc(h, alice), opened["id"])["queue"]
    assert again == block


def test_the_listing_of_everyones_still_reads_nothing_of_its_own(h: Harness) -> None:  # noqa: F811
    alice = h.token_for("code_alice", "alice-p")
    opened = annex(h, alice)
    listed = h.client.get("/submissions.json").json()
    block = next(e for e in listed["open"] if e["id"] == opened["id"])["queue"]
    assert block["waiting_on"] is None and block["waiting_on_read_at"] is None
