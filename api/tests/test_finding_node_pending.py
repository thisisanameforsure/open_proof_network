"""Finding node-pending (the 2026-09-19 primes run, all four agents): every call on a node that
existed only in an open proposal, or had merged minutes ago, answered ``404 node-unknown``, "is
not a node of this graph" — the same words a node that was never proposed gets. An agent could
not tell a typo from "wait for a maintainer" from "wait for the products", and polled the 404.

F08-T11: the service recorded the proposal it opened (F07-T16), so it can say which it is —
``409 node-pending`` naming the pull request and what it waits for, ``409 products-pending``
with ``Retry-After`` once it has merged, and ``404 node-unknown`` only for a node nobody
proposed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from api_fakes import Harness
from test_pending_submissions import record, store  # noqa: F401 — store: a both-stores fixture
from test_precheck import bundle_for, post

from opn_api.store import Store, Submission

NEW_NODE = "variant-0badc0de"


def proposal(number: int, **overrides: Any) -> Submission:
    return record(number, kind="variant", node_id=NEW_NODE, **overrides)


def test_a_proposal_is_found_by_its_node_in_both_stores(store: Store) -> None:  # noqa: F811
    first = proposal(3)
    store.put_submission(first)
    store.put_submission(record(4, kind="annex", node_id=NEW_NODE))  # an append is not a proposal
    assert store.get_submission_by_node(NEW_NODE) == first
    assert store.get_submission_by_node("variant-ffffffff") is None
    # closing keeps it findable: the agents' own polling closes the record at the merge
    closed = store.close_submission(first.id, closed="t", final_state={"merged": True})
    assert store.get_submission_by_node(NEW_NODE) == closed
    # a second proposal of the same statement (the first was closed unmerged) is the one found
    again = replace(proposal(5), id="01M" + "9" * 23)
    store.put_submission(again)
    assert store.get_submission_by_node(NEW_NODE) == again


def precheck_new_node(h: Harness, token: str) -> Any:
    return post(h, {"node_id": NEW_NODE, "bundle": bundle_for(NEW_NODE)}, token)


@pytest.fixture
def token(harness: Harness) -> str:
    return harness.token_for("code_alice", "alice-p")


def test_an_open_proposal_says_what_it_waits_for(harness: Harness, token: str) -> None:
    harness.store.put_submission(proposal(7))
    harness.githost.set_pull_request_state(
        7,
        mergeable_state="clean",
        runs=[{"name": "gate", "status": "completed", "conclusion": "success"}],
    )
    r = precheck_new_node(harness, token)
    assert r.status_code == 409, r.text
    doc = r.json()
    assert doc["error"] == "node-pending"
    assert "#7" in doc["message"] and "merge" in doc["message"]
    assert doc["details"] == {
        "pr_number": 7,
        "pr_url": "https://github.com/pr/7",
        "waiting_on": "merge",
    }


def test_a_merged_proposal_says_the_products_are_pending(harness: Harness, token: str) -> None:
    harness.store.put_submission(proposal(7))
    harness.githost.set_pull_request_state(7, state="closed", merged=True)
    r = precheck_new_node(harness, token)
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "products-pending"
    assert int(r.headers["Retry-After"]) > 0
    assert r.json()["details"]["pr_number"] == 7

    # ...and the same once the record was closed by an earlier read
    harness.store.close_submission(proposal(7).id, closed="t", final_state={"merged": True})
    assert precheck_new_node(harness, token).json()["error"] == "products-pending"


@pytest.mark.parametrize("closed_unmerged", [True, False])
def test_a_node_nobody_proposed_or_a_closed_proposal_is_still_unknown(
    harness: Harness, token: str, closed_unmerged: bool
) -> None:
    if closed_unmerged:
        harness.store.put_submission(proposal(7))
        harness.githost.set_pull_request_state(7, state="closed", merged=False)
    r = precheck_new_node(harness, token)
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "node-unknown"
    assert "post-merge" in r.json()["message"]


def test_a_host_failure_never_hides_the_node_behind_a_500(harness: Harness, token: str) -> None:
    """C7: the pull request cannot be read, so say it is pending and name it."""
    harness.store.put_submission(proposal(7))
    harness.githost.pr_lookup_failure = "boom"
    r = precheck_new_node(harness, token)
    assert r.status_code == 409 and r.json()["error"] == "node-pending"
    assert r.json()["details"]["waiting_on"] is None
