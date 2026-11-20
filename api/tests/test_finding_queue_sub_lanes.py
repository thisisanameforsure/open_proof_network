"""F07-T83 (bug B1, agent run 2026-11-19): a position counts the pull request's own sub-lane.

Six of nine agents saw green appends (postmortems, annexes, explainers, glosses, literature) sit
20 to 50 minutes behind proofs and partials on their target, whose gate takes minutes and whose
branch is updated after every merge on it. The merge actor now splits each target's lane in two
(F07-T81/T82, the graph's ``merge.yml``): appends, the pull requests on the service's ``append/``
branches, and building pull requests, on ``propose/`` and ``submit/``. A building pull request
never holds an append back and an append never holds a building one back. A pull request the
service cannot place in one target still waits for every lane, both halves of every target.

The service's ``queue`` block mirrors that: ``position``, ``of`` and ``ahead`` count the pull
requests in the same ``(target, append-or-build)`` sub-lane, plus every one it cannot place.
Which half a pull request is in is read from the open listing's ``head_ref`` (the actor's own
fact), and from the record's ``kind`` where there is no listing entry (``pending.sub_lane``).

F07-T86 (bug B17 b): the position jittered 8 -> 9 -> 8. A pull request that merged on another
target, whose record a per-id read had already closed, was still in the open listing for up to a
minute; with no open record the service could not place it, so it was counted ahead in *every*
lane until the listing was read again. A listed pull request whose record is closed has finished,
and is counted in no lane.
"""

from __future__ import annotations

from dataclasses import replace

from api_fakes import Harness
from test_finding_queue_lanes import OTHER, move_to_other_target
from test_finding_queue_position import listing, three_annexes
from test_pending_submissions import get

from opn_api import pending, submissions
from opn_api.githost import OpenPullRequest
from opn_api.store import Submission


def as_proof(h: Harness, number: int) -> None:
    """Make ``number`` a proof the service opened on ``submit/``: its record and its branch."""
    record = h.store.get_submission_by_pr(number)
    assert record is not None
    h.store.put_submission(replace(record, kind="proof"))
    h.githost.set_pull_request_state(number, head_ref=f"submit/{record.id}")


def place(h: Harness, number: int) -> tuple[list[int], int | None, int | None]:
    queue = get(h, str(number))["queue"]
    return [a["pr_number"] for a in queue["ahead"]], queue["position"], queue["of"]


def test_an_append_is_not_counted_behind_a_proof_on_its_target(harness: Harness) -> None:
    three_annexes(harness)  # #1, #2, #3 on the tutorial target, all append/
    as_proof(harness, 1)
    assert place(harness, 3) == ([2], 2, 2)
    assert place(harness, 2) == ([], 1, 2)


def test_a_proof_is_not_counted_behind_an_append_on_its_target(harness: Harness) -> None:
    three_annexes(harness)
    as_proof(harness, 3)
    assert place(harness, 3) == ([], 1, 1)


def test_the_listing_counts_each_entry_in_its_own_sub_lane(harness: Harness) -> None:
    three_annexes(harness)
    as_proof(harness, 2)
    doc = listing(harness)
    by_number = {e["pr_number"]: e["queue"] for e in doc["open"]}
    assert {n: (q["position"], q["of"]) for n, q in by_number.items()} == {
        1: (1, 2),
        2: (1, 1),
        3: (2, 2),
    }
    assert doc["queue"]["order"] == [1, 2, 3]  # the actor's whole order is unchanged


def test_an_unplaced_pull_request_is_ahead_in_both_halves(harness: Harness) -> None:
    three_annexes(harness)
    as_proof(harness, 2)
    harness.githost.set_pull_request_state(22, head_ref="append/unrecorded")
    first = get(harness, "1")["queue"]  # an append: #3 and the unplaced #22
    assert (first["position"], first["of"]) == (1, 3)
    proof = get(harness, "2")["queue"]  # a proof: itself and the unplaced #22
    assert (proof["position"], proof["of"]) == (1, 2)


def test_the_branch_decides_and_the_kind_is_the_fallback() -> None:
    record = Submission(
        id="01M00000000000000000000001",
        kind="annex",
        node_id=None,
        target_id="t",
        pr_number=1,
        pr_url="u",
        pseudonym="alice",
        precheck_job_id=None,
        created="2026-09-09T12:00:00Z",
    )

    def entry(ref: str) -> OpenPullRequest:
        return OpenPullRequest(1, "u", "0" * 40, head_ref=ref)

    assert pending.sub_lane(record, entry("submit/x")) == pending.SUB_BUILD
    assert pending.sub_lane(replace(record, kind="proof"), entry("append/x")) == pending.SUB_APPEND
    assert pending.sub_lane(record, None) == pending.SUB_APPEND
    for kind in ("proof", "partial", "speculative", "variant", "witness"):
        assert pending.sub_lane(replace(record, kind=kind), None) == pending.SUB_BUILD
    assert pending.branch_sub_lane(submissions.APPEND_BRANCH_PREFIX + "x") == pending.SUB_APPEND
    assert pending.branch_sub_lane(submissions.SUBMIT_BRANCH_PREFIX + "x") == pending.SUB_BUILD
    assert pending.APPEND_PREFIX == submissions.APPEND_BRANCH_PREFIX


def test_the_text_describes_the_two_halves() -> None:
    assert "append" in pending.QUEUE_ORDER and "propose/" in pending.QUEUE_ORDER
    assert "half" in pending.QUEUE_NOTE


# --- F07-T86 (B17 b): a merge the listing still carries ------------------------------------------


def test_a_merged_pull_request_the_listing_still_carries_is_ahead_of_nobody(
    harness: Harness,
) -> None:
    three_annexes(harness)
    move_to_other_target(harness, 1)  # #1 on erdos-69; #2, #3 on the tutorial target
    assert place(harness, 3) == ([2], 2, 2)
    harness.githost.set_pull_request_state(1, state="closed", merged=True)
    harness.context.pulls.clear()  # the per-id state is past its window; the listing is not
    assert get(harness, "1")["state"] == "merged"  # a per-id read closes its record
    closed = harness.store.get_submission_by_pr(1)
    assert closed is not None and closed.closed is not None and closed.target_id == OTHER
    assert harness.context.open_pulls is not None and 1 in harness.context.open_pulls.by_number
    assert place(harness, 3) == ([2], 2, 2)  # was ([1, 2], 3, 3) until the listing refreshed
    by_number = {e["pr_number"]: e["queue"] for e in listing(harness)["open"]}
    assert (by_number[3]["position"], by_number[3]["of"]) == (2, 2)
