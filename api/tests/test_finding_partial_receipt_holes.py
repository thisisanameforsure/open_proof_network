"""Testers 2026-10-09 (A, feature; the owner: "you can do: the future hole ids in a partial's
receipt"): a partial's receipt did not say which nodes its holes would become, so a contributor
polled ``get_node`` for minutes after the merge to learn the ids.

The precheck job now names each hole's expected node (``expected_node_id``, ``expected_new``) by
the post-merge writer's own rule, over the tree the job ran at. The submission's receipt carries
them with ``holes_note``: they are expected, not promised, because another decomposition of the
node merging first renumbers them (R22). A precheck from a gate that names none leaves the
receipt as it was.
"""

from __future__ import annotations

import pytest
from api_fakes import TUTORIAL_PROOF, Harness, PrecheckKey, make_precheck_key
from test_finding_partial_witnesses import PARTIAL_PATH, hole, passing_job, submit

BUNDLE = {PARTIAL_PATH: TUTORIAL_PROOF}


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def test_the_receipt_names_each_holes_expected_node(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    holes = [
        {**hole("left"), "expected_node_id": "tutorial-and-swap--h3", "expected_new": True},
        {**hole("right"), "expected_node_id": "tutorial-and-swap--h1", "expected_new": False},
    ]
    job = passing_job(harness, key, token, BUNDLE, holes)
    r = submit(harness, token, BUNDLE, job)
    assert r.status_code == 201, r.text
    receipt = r.json()
    assert receipt["holes"] == [
        {"name": "left", "expected_node_id": "tutorial-and-swap--h3", "expected_new": True},
        {"name": "right", "expected_node_id": "tutorial-and-swap--h1", "expected_new": False},
    ]
    assert "merging first" in receipt["holes_note"]


def test_a_result_that_names_no_node_leaves_the_receipt_as_it_was(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, BUNDLE, [hole("left")])
    receipt = submit(harness, token, BUNDLE, job).json()
    assert "holes" not in receipt and "holes_note" not in receipt
