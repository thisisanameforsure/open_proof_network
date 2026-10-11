"""F07-T69 (audit 2026-10-04): a submission's queue position is counted in its own target's lane.

The merge actor has been strict per target since F07-T56: one lane per target (the graph's
``merge.yml``, ``lane_of_paths``), lanes going in parallel, oldest first within a lane. A pull
request the actor cannot place in one target goes in no lane: it waits until it is first and then
holds every lane (``EVERY_LANE``). The service's ``queue`` block still counted every open pull
request on the graph, so an agent on one target was told it stood behind another target's queue,
which cannot delay it.

The service knows a pull request's lane from its own record of it: every route that opens one
records the one target it touches (``Submission.target_id``). A pull request the actor takes but
the service has no open record of has no known lane, and is counted in every lane, as the actor
treats one it cannot place; the position stays an upper bound.
"""

from __future__ import annotations

from dataclasses import replace

from api_fakes import Harness
from test_finding_queue_position import listing, three_annexes
from test_pending_submissions import get

from opn_api import pending

OTHER = "erdos-69"


def move_to_other_target(h: Harness, number: int) -> None:
    record = h.store.get_submission_by_pr(number)
    assert record is not None
    h.store.put_submission(replace(record, target_id=OTHER))


def test_a_position_counts_only_its_own_targets_lane(harness: Harness) -> None:
    three_annexes(harness)  # #1, #2, #3 on the tutorial target
    move_to_other_target(harness, 2)
    queue = get(harness, "3")["queue"]
    assert [a["pr_number"] for a in queue["ahead"]] == [1]
    assert (queue["position"], queue["of"]) == (2, 2)
    other = get(harness, "2")["queue"]
    assert (other["position"], other["of"], other["ahead"]) == (1, 1, [])


def test_the_listing_counts_each_entry_in_its_own_lane(harness: Harness) -> None:
    three_annexes(harness)
    move_to_other_target(harness, 2)
    doc = listing(harness)
    by_number = {e["pr_number"]: e["queue"] for e in doc["open"]}
    assert {n: (q["position"], q["of"]) for n, q in by_number.items()} == {
        1: (1, 2),
        2: (1, 1),
        3: (2, 2),
    }
    # the whole order is still the actor's, across every lane
    assert doc["queue"]["order"] == [1, 2, 3]


def test_an_unplaced_pull_request_is_ahead_in_every_lane(harness: Harness) -> None:
    """One the actor takes and the service has no record of: its lane is not known, so it is
    counted in every lane (the actor holds every lane for one it cannot place)."""
    three_annexes(harness)
    move_to_other_target(harness, 2)
    harness.githost.set_pull_request_state(22, head_ref="propose/unrecorded")
    harness.githost.set_pull_request_state(23, head_ref="submit/unrecorded")
    first = get(harness, "1")["queue"]
    assert (first["position"], first["of"]) == (1, 4)  # 22 and 23 are younger, still counted
    other = get(harness, "2")["queue"]
    assert (other["position"], other["of"]) == (1, 3)


def test_the_text_describes_the_lanes() -> None:
    assert "lane" in pending.QUEUE_ORDER and "target" in pending.QUEUE_ORDER
    assert "upper bound" in pending.QUEUE_ORDER and "passes over" in pending.QUEUE_ORDER
