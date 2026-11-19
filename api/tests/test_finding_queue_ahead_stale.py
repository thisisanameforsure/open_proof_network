"""F07-T80 (bug B7, agent run 2026-11-19): ``queue.ahead`` names pull requests nobody waits on.

Witness pull request #1489 on the graph (node ``variant-cce9b284--h6``) opened on 2026-11-13, its
gate failed the same day and it has had no update since; #1504 has since merged and filled that
witness slot. It was still the first entry of ``queue.ahead`` for every erdos-257 submission. The
merge actor passes over a red pull request (``merge.yml``'s ``decide``), so it never delayed a
merge: the block was telling every agent on the target to wait behind something that cannot
merge and that the record no longer needs.

The owner's ruling (2026-11-19): drop such pull requests from ``ahead`` only; close nothing.
Dropped, and left out of ``position`` and ``of`` with them so the three agree:

* (a) a pull request the service opened as a witness whose node's slot ``main`` already fills;
* (b) a pull request whose gate failed and that the host says has not been updated for more than
  ``OPN_API_QUEUE_IDLE_RED_DAYS`` days (default 3).

``queue.order`` in ``GET /submissions.json`` stays the actor's own order (the actor still lists
both; ``gate/tests/test_finding_queue_order_is_the_actors.py`` holds that).
"""

from __future__ import annotations

from dataclasses import replace

from api_fakes import Harness
from test_finding_queue_position import listing, three_annexes
from test_pending_submissions import age, get

from opn_api import config, pending

HOLE = "tutorial-and-swap--h1"
RED = {"name": "gate", "status": "completed", "conclusion": "failure", "url": "u"}
GREEN = {"name": "gate", "status": "completed", "conclusion": "success", "url": "u"}
# the fake clock reads 2026-09-09T12:00:00Z
FOUR_DAYS_AGO = "2026-09-05T12:00:00Z"
TWO_DAYS_AGO = "2026-09-07T12:00:00Z"
FILLED = b"theorem OpnFixture.w : True := trivial\n"
STUB = b"-- witness slot: replace the sorry\ntheorem OpnFixture.w : True := by\n  sorry\n"


def as_witness(h: Harness, number: int, slot: bytes | None) -> None:
    """Make the service's record of ``number`` a witness for ``HOLE``, with ``slot`` as the hole's
    ``Witness.lean`` on ``main`` (``None``: no file there)."""
    record = h.store.get_submission_by_pr(number)
    assert record is not None
    h.store.put_submission(replace(record, kind="witness", node_id=HOLE))
    path = f"targets/{record.target_id}/nodes/{HOLE}/Witness.lean"
    if slot is None:
        h.githost.files.pop(path, None)
    else:
        h.githost.files[path] = slot


def ahead_of(h: Harness, number: int) -> tuple[list[int], int | None, int | None]:
    queue = get(h, str(number))["queue"]
    return [a["pr_number"] for a in queue["ahead"]], queue["position"], queue["of"]


# --- (a) a witness for a slot main already fills ------------------------------------------------


def test_a_witness_for_a_slot_main_has_filled_is_not_ahead(harness: Harness) -> None:
    three_annexes(harness)
    as_witness(harness, 1, FILLED)
    assert ahead_of(harness, 3) == ([2], 2, 2)


def test_a_witness_for_a_slot_still_a_stub_stays_ahead(harness: Harness) -> None:
    three_annexes(harness)
    as_witness(harness, 1, STUB)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


def test_a_witness_for_a_slot_with_no_file_stays_ahead(harness: Harness) -> None:
    three_annexes(harness)
    as_witness(harness, 1, None)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


# --- (b) a red pull request left idle -------------------------------------------------------------


def test_a_red_pull_request_idle_past_the_window_is_not_ahead(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=FOUR_DAYS_AGO)
    assert ahead_of(harness, 3) == ([2], 2, 2)


def test_a_red_pull_request_idle_inside_the_window_stays(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=TWO_DAYS_AGO)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


def test_a_green_pull_request_however_old_stays(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[GREEN], updated_at=FOUR_DAYS_AGO)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


def test_an_old_pull_request_still_running_stays(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[], updated_at=FOUR_DAYS_AGO)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


def test_the_window_is_configuration(harness: Harness) -> None:
    assert config.DEFAULT_QUEUE_IDLE_RED_DAYS == 3
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=TWO_DAYS_AGO)
    harness.context.settings = replace(harness.context.settings, queue_idle_red_days=1)
    assert ahead_of(harness, 3) == ([2], 2, 2)


def test_the_window_reads_from_the_environment() -> None:
    assert config.load({}).queue_idle_red_days == 3
    assert config.load({"OPN_API_QUEUE_IDLE_RED_DAYS": "7"}).queue_idle_red_days == 7


def test_an_idle_pull_request_the_host_cannot_describe_stays(harness: Harness) -> None:
    """No state is not a red state: the position stays an upper bound (C7)."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=FOUR_DAYS_AGO)
    harness.githost.pull_failures.add(1)
    assert ahead_of(harness, 3) == ([1, 2], 3, 3)


def test_only_idle_pull_requests_cost_a_state_read(harness: Harness) -> None:
    """The listing's ``updated_at`` is free; a state read is spent only on one the listing says
    has been idle past the window, and is cached like any other (C7)."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=FOUR_DAYS_AGO)
    harness.githost.set_pull_request_state(2, runs=[RED], updated_at=TWO_DAYS_AGO)
    get(harness, "3")
    get(harness, "3")
    assert sorted(harness.githost.pull_lookups) == [1, 3]


def test_a_red_idle_head_is_read_once_per_process(harness: Harness) -> None:
    """An abandoned pull request's state is not re-read every window: its red head is
    remembered. A push moves the head and the listing's ``updated_at``, so it is judged anew."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=FOUR_DAYS_AGO)
    assert ahead_of(harness, 3)[0] == [2]
    age(harness)
    harness.githost.pull_lookups.clear()
    assert ahead_of(harness, 3)[0] == [2]
    assert 1 not in harness.githost.pull_lookups
    harness.githost.set_pull_request_state(
        1, runs=[], head_sha="f" * 40, updated_at="2026-09-09T11:00:00Z"
    )
    age(harness)
    assert ahead_of(harness, 3)[0] == [1, 2]


# --- the listing agrees ---------------------------------------------------------------------------


def test_the_listing_counts_positions_without_them(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RED], updated_at=FOUR_DAYS_AGO)
    doc = listing(harness)
    by_number = {e["pr_number"]: e["queue"] for e in doc["open"]}
    assert (by_number[2]["position"], by_number[2]["of"]) == (1, 2)
    assert (by_number[3]["position"], by_number[3]["of"]) == (2, 2)
    # its own entry still says where it stands, among the ones it is behind
    assert (by_number[1]["position"], by_number[1]["of"]) == (1, 3)
    # the actor's order is the actor's: it still lists the red one
    assert doc["queue"]["order"] == [1, 2, 3]


def test_a_dropped_pull_request_still_has_its_own_position(harness: Harness) -> None:
    three_annexes(harness)
    as_witness(harness, 2, FILLED)
    assert ahead_of(harness, 2) == ([1], 2, 3)


def test_the_text_says_so() -> None:
    assert "idle" in pending.QUEUE_ORDER and "witness" in pending.QUEUE_ORDER
