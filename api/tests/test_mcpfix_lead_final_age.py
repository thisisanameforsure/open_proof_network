"""mcpfix (lead; verifier VB, N4, 2026-11-25): a closed pull request's block is the host's last
word, so it carries no age.

VB followed #2061 for eighteen minutes after it merged: ``read_at`` stayed at the merge read and
``age_s`` stayed 0, which reads as "just read". A closed record's stored block now answers
``age_s: null`` (the final snapshot) and ``stale: false``."""

from __future__ import annotations

from api_fakes import Harness
from test_pending_submissions import proof_record


def test_a_merged_pull_requests_block_has_no_age(harness: Harness) -> None:
    proof_record(harness)
    harness.githost.set_pull_request_state(
        7, state="closed", merged=True, merge_commit_sha="9" * 40, merged_at="2026-09-09T16:00:00Z"
    )
    first = harness.client.get("/submissions/7").json()["pull_request"]
    assert first["merged"] is True
    harness.clock.advance(minutes=18)
    later = harness.client.get("/submissions/7").json()["pull_request"]
    assert later["read_at"] == first["read_at"]
    assert later["age_s"] is None
    assert later["stale"] is False
