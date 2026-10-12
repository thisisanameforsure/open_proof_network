"""F06-T17 (decisions v3.38, D-12; testers 2026-10-09b, C1): a partial's receipt says what a
hole that restates a node under another branch becomes.

F06-T15's receipt named such a hole with ``expected_new: false`` and a note that read "a hole
restating an existing node is that node", which to the agent of C1 meant nothing would happen —
and under the old rule nothing did (F07-R22). Under v3.38 the node becomes a *lemma* of the
parent: usable once proved, never waited on, its theorem in the parent's ``Context.lean``. The
note says so; the precheck's own result document is unchanged (the gate computes
``expected_new``).
"""

from __future__ import annotations

import pytest
from api_fakes import TUTORIAL_PROOF, Harness, PrecheckKey, make_precheck_key
from test_finding_partial_witnesses import PARTIAL_PATH, hole, passing_job, submit

from opn_api import submissions

BUNDLE = {PARTIAL_PATH: TUTORIAL_PROOF}
EXISTING = "already-proved"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def test_the_receipts_note_says_a_restating_hole_becomes_a_lemma(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    holes = [
        {**hole("left"), "expected_node_id": "tutorial-and-swap--h3", "expected_new": True},
        {**hole("right"), "expected_node_id": EXISTING, "expected_new": False},
    ]
    job = passing_job(harness, key, token, BUNDLE, holes)
    r = submit(harness, token, BUNDLE, job)
    assert r.status_code == 201, r.text
    note = r.json()["holes_note"]
    assert "lemma of this node" in note
    assert "once it is proved" in note
    assert "never waits on it" in note
    assert "Context.lean" in note
    assert "merging first" in note  # F06-T15's half still stands
    # the precheck's result document is the gate's, unchanged: the receipt repeats its fields
    assert r.json()["holes"][1] == {
        "name": "right",
        "expected_node_id": EXISTING,
        "expected_new": False,
    }


def test_a_result_naming_no_hole_has_no_note() -> None:
    assert submissions.hole_rows({"holes": [{"name": "left"}]}, "1" * 40) == {}
    assert submissions.hole_rows(None, "1" * 40) == {}
