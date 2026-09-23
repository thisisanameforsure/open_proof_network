"""F07-T35: a copy is refused before a pull request opens (testers 2026-09-23; D-25 v3.21).

Nine agents on three targets: every write route opened a pull request without looking at what was
already open for the node. #150 was a second witness for ``erdos-1050--h1-v2--h1``, identical but
for its comments to #146, opened while #146 was still in its gate; it could never merge, and read
``waiting_on: merge`` until a person closed it. #168 and #171 proposed the same statement. The
owner's rule: a node may carry many different proofs, never two copies of one; a hole has one
witness slot; a statement is proposed once. So:

* a proof (or partial, or alternate) whose text matches, comments and whitespace aside, a proof
  already merged on the node or open for it is ``409 duplicate-submission`` naming it;
* a witness for a hole with a witness already open is refused whatever it says (one slot);
* a proposal of a statement already proposed and open is refused;
* an annex, postmortem or approach record identical to one open for the same node is refused;
* a pull request whose gate failed, or that conflicts, or that is closed blocks nothing, so a
  corrected resubmission (#171 after #168) goes through;
* and two identical requests in the same seconds cannot both pass.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import PROOF_PREFIX, Harness, PrecheckKey, make_precheck_key
from test_pending_submissions import record, store  # noqa: F401 — store: a both-stores fixture
from test_proposals import (
    HOLE,
    RELATION_PROOF,
    STATEMENT,
    TARGET,
    WITNESS,
    add_hole,
    post,
)
from test_submissions_alternate import mark_proved, passing_job, submit

from opn_api import duplicates
from opn_api.store import Store

GATE_FAILED = [{"name": "gate", "status": "completed", "conclusion": "failure", "url": "r"}]
PROOF = "import Mathlib\n\ntheorem x : True := by\n  trivial\n"
SAME_PROOF_REWORDED = (
    "import Mathlib\n\n/-- the obvious proof -/\ntheorem x : True := by  -- done\n    trivial\n"
)
OTHER_PROOF = "import Mathlib\n\ntheorem x : True := True.intro\n"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def opened(h: Harness) -> int:
    return len(h.githost.pulls)


# --- the normalisation ---------------------------------------------------------------------------


def test_comments_and_whitespace_do_not_make_a_different_proof() -> None:
    assert duplicates.fingerprint(PROOF) == duplicates.fingerprint(SAME_PROOF_REWORDED)
    assert duplicates.fingerprint(PROOF) != duplicates.fingerprint(OTHER_PROOF)
    nested = "theorem x : True := /- a /- nested -/ comment -/ trivial"
    assert duplicates.normalise(nested) == "theorem x : True := trivial"


# --- a witness: one slot --------------------------------------------------------------------------


def test_a_second_witness_while_one_is_open_is_refused(harness: Harness) -> None:
    """#146 then #150."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    add_hole(harness)
    first = post(harness, "/proposals/witness", alice, {"node_id": HOLE, "witness": WITNESS})
    assert first.status_code == 201, first.text
    before = opened(harness)
    second = post(
        harness,
        "/proposals/witness",
        bob,
        {"node_id": HOLE, "witness": "-- mine\n" + WITNESS},
    )
    assert second.status_code == 409, second.text
    body = second.json()
    assert body["error"] == "duplicate-submission"
    assert body["details"]["pr_number"] == first.json()["pr_number"]
    assert opened(harness) == before, "nothing may be opened for a refused copy"


def test_a_witness_after_the_open_one_failed_its_gate_goes_through(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    first = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert first.status_code == 201, first.text
    harness.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    harness.clock.advance(minutes=5)  # a gate round later, out of the first request's window
    again = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert again.status_code == 201, again.text


def test_a_witness_after_the_open_one_was_closed_goes_through(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    first = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    harness.githost.set_pull_request_state(first.json()["pr_number"], state="closed")
    harness.clock.advance(minutes=5)
    again = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert again.status_code == 201, again.text


# --- a proposal: one per statement ----------------------------------------------------------------


def variant(h: Harness, token: str) -> Any:
    body = {
        "target_id": TARGET,
        "statement": STATEMENT,
        "witness": WITNESS,
        "relation": "partial",
        "relation_proof": RELATION_PROOF,
    }
    return post(h, "/proposals/variant", token, body)


def test_the_same_statement_proposed_twice_is_refused(harness: Harness) -> None:
    """#168 and #171."""
    token = harness.token_for("code_alice", "alice")
    first = variant(harness, token)
    assert first.status_code == 201, first.text
    before = opened(harness)
    second = variant(harness, harness.token_for("code_bob", "bob"))
    assert second.status_code == 409, second.text
    assert second.json()["error"] == "duplicate-submission"
    assert second.json()["details"]["pr_number"] == first.json()["pr_number"]
    assert opened(harness) == before


def test_a_statement_whose_proposal_failed_its_gate_may_be_proposed_again(
    harness: Harness,
) -> None:
    """#171 corrected #168's witness; it is a new attempt, not a copy of an open one."""
    token = harness.token_for("code_alice", "alice")
    first = variant(harness, token)
    harness.githost.set_pull_request_state(first.json()["pr_number"], runs=GATE_FAILED)
    harness.clock.advance(minutes=5)
    again = variant(harness, token)
    assert again.status_code == 201, again.text


# --- a proof: many proofs, no copies --------------------------------------------------------------


def test_a_copy_of_an_open_proof_is_refused_and_a_different_proof_is_not(
    harness: Harness, key: PrecheckKey
) -> None:
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    _proved, node = mark_proved(harness)
    path = f"{PROOF_PREFIX}{node}/Proof.lean"
    first = submit(
        harness, alice, node, {path: PROOF}, passing_job(harness, key, alice, node, {path: PROOF})
    )
    assert first.status_code == 201, first.text
    copy = {path: SAME_PROOF_REWORDED}
    before = opened(harness)
    refused = submit(harness, bob, node, copy, passing_job(harness, key, bob, node, copy))
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"] == "duplicate-submission"
    assert refused.json()["details"]["pr_number"] == first.json()["pr_number"]
    assert opened(harness) == before
    other = {path: OTHER_PROOF}
    raced = submit(harness, bob, node, other, passing_job(harness, key, bob, node, other))
    assert raced.status_code == 201, raced.text  # a different proof races, as D-25 allows


def test_an_alternate_that_copies_the_merged_proof_is_refused(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    proved, _node = mark_proved(harness)
    harness.githost.files[f"{PROOF_PREFIX}{proved}/Proof.lean"] = PROOF.encode()
    path = f"{PROOF_PREFIX}{proved}/attempts/20260923T120000Z-alice-alternate.lean"
    alternate = {path: SAME_PROOF_REWORDED}
    got = submit(
        harness, token, proved, alternate, passing_job(harness, key, token, proved, alternate)
    )
    assert got.status_code == 409, got.text
    assert got.json()["error"] == "duplicate-submission"
    assert got.json()["details"]["path"].endswith("/Proof.lean")


# --- appends --------------------------------------------------------------------------------------


def annex(h: Harness, token: str, text: str) -> Any:
    return post(
        h, "/annexes", token, {"node_id": "and-reassoc", "licence": "CC-BY-4.0", "text": text}
    )


def test_an_identical_annex_while_one_is_open_is_refused_and_a_different_one_is_not(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    text = "The hole is the root again: the first two terms cancel.\n"
    first = annex(harness, token, text)
    assert first.status_code == 201, first.text
    copy = annex(harness, harness.token_for("code_bob", "bob"), text)
    assert copy.status_code == 409, copy.text
    assert copy.json()["error"] == "duplicate-submission"
    other = annex(harness, token, "A different remark.\n")
    assert other.status_code == 201, other.text


# --- the race -------------------------------------------------------------------------------------


def test_two_identical_requests_in_the_same_seconds_cannot_both_pass(harness: Harness) -> None:
    """The open-record check runs before the record exists; the claim on the slot is atomic."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    duplicates.claim_slot(harness.context, duplicates.slot("witness", HOLE))  # the other request
    got = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert got.status_code == 409, got.text
    assert got.json()["error"] == "duplicate-submission"
    assert 0 < int(got.headers["Retry-After"]) <= duplicates.SLOT_WINDOW_S


def test_a_request_refused_for_another_reason_holds_no_slot(harness: Harness) -> None:
    """The slot is taken last: a witness refused as a sorry does not block the corrected one a
    second later."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    stub = {"node_id": HOLE, "witness": "theorem witness : True := by\n  sorry\n"}
    assert post(harness, "/proposals/witness", token, stub).status_code == 400
    got = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert got.status_code == 201, got.text


def test_a_push_that_fails_gives_its_slot_back(harness: Harness) -> None:
    """A request whose pull request never opened holds nothing: the same request goes through at
    once when the host answers again (C7)."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    harness.githost.app_failure = "POST /repos/g/git/trees returned 502"
    failed = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert failed.status_code == 502, failed.text
    harness.githost.app_failure = None
    again = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert again.status_code == 201, again.text


def test_fingerprints_and_the_slot_counter_in_both_stores(store: Store) -> None:  # noqa: F811
    """The record keeps its fingerprints through either store, and a dropped counter starts
    again from one (the parity the seam owes, conventions §1)."""
    from dataclasses import replace  # noqa: PLC0415 — one use
    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    kept = replace(record(9, kind="proof", node_id="n"), fingerprints=("a" * 64, "b" * 64))
    store.put_submission(kept)
    got = store.get_submission(kept.id)
    assert got is not None and got.fingerprints == kept.fingerprints
    later = datetime(2026, 9, 23, tzinfo=UTC) + timedelta(minutes=5)
    assert store.bump_counter("dup#k", later) == 1
    assert store.bump_counter("dup#k", later) == 2
    store.drop_counter("dup#k")
    assert store.bump_counter("dup#k", later) == 1


def test_the_tutorial_node_may_be_rehearsed_again_and_again(harness: Harness) -> None:
    """D-27 keeps the tutorial node open to rehearsal: its merged proof resubmitted is the guide's
    first exercise, and every newcomer does it (the guide's walkthrough and the rehearsal tool)."""
    assert (
        duplicates.check_proof(
            harness.context, TARGET, "tutorial", {"x.lean": PROOF}, tutorial=True
        )
        == []
    )


def test_a_copied_proposal_spends_no_hosted_check(harness: Harness) -> None:
    """The duplicate rule runs before F13-T16's witness pre-flight, so a refused copy costs the
    caller nothing of the hosted checker's budget."""
    token = harness.token_for("code_alice", "alice")
    assert variant(harness, token).status_code == 201
    asked = len(harness.axle.calls)
    assert variant(harness, harness.token_for("code_bob", "bob")).status_code == 409
    assert len(harness.axle.calls) == asked
