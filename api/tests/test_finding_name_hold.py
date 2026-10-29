"""Testers 2026-10-27 (erdos-849), D's F-D9: a record's path is held while it is being filed and
while an open pull request files at it, and not a moment longer.

The story. D filed an explainer (#1091), withdrew it 50 s later, and filed the identical text
again three minutes on: ``409 record-name-taken``, "a record of yours is already being filed at
…/explainer/844ecfba….md this second: a record's file name is <timestamp>-<pseudonym> to the
second (D-13) … Send it again after Retry-After". Retried after 5 s and a minute later: the same.
An explainer is named by its content hash, not by a second, and the pull request that had held
the path was closed.

The mechanism. ``appends.holding_name`` bumped a counter keyed ``name#<path>`` with a 60 s
expiry and refused whenever the count passed 1. The key named no window, the success path never
dropped it, the memory store never expires a counter, and DynamoDB sets ``expires_at`` only
``if_not_exists`` and counts an expired item until the TTL sweep: a hold meant for one second
lasted hours, on every path that can recur (content-named words and annexes, numbered steward
and panel records). On ``<timestamp>-<pseudonym>`` paths it never showed, because those name
their second.

The rule now. Two guards. In flight: a counter keyed by the path *and* a window, as
``duplicates.counter_key`` is, dropped once the submission is recorded and lapsing with its
window if the process dies. Standing: an open submission that files at the path (a ``path:``
print among its fingerprints) holds it, named in the refusal, until it merges or is withdrawn.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from test_stewards_route import (  # noqa: F401 — fixtures: the graph tree and the approval key
    approval,
    h,
    keys,
    post,
    tree,
)
from test_store_seam import dynamo
from test_web_session import sign_in

from opn_api import appends
from opn_api.app import ApiError
from opn_api.store import MemoryStore

ANNEX_TEXT = "An informal argument, filed twice.\n"


@pytest.fixture(params=["memory", "dynamodb"])
def both(request: pytest.FixtureRequest) -> Iterator[Harness]:
    store = MemoryStore() if request.param == "memory" else dynamo()
    harness = make_harness(store=store)
    with harness.client:
        yield harness


def annex(harness: Harness, token: str) -> Any:
    return harness.client.post(
        "/annexes",
        json={"node_id": TUTORIAL_NODE, "text": ANNEX_TEXT, "licence": "CC-BY-4.0"},
        headers=harness.auth(token),
    )


#: An explainer's path is its text's hash, and its file carries no time (F20), so the same words
#: are the same file however much later they are sent.
WORDS_PATH = f"targets/propositional/nodes/{TUTORIAL_NODE}/explainer/844ecfba.md"


def explainer(
    harness: Harness, pseudonym: str = "alice", content: str = "The same words.\n"
) -> dict[str, Any]:
    """D's explainer, sent through the shared append (the route's own checks need a graph
    with a merged proof and an outline, which the finding is not about)."""
    me = harness.store.get_identity_by_pseudonym(pseudonym)
    assert me is not None
    return appends.append_pr(
        harness.context,
        me,
        path=WORDS_PATH,
        content=content,
        subject=f"explainer: {TUTORIAL_NODE}",
        what="explainer",
        kind="explainer",
        target_id="propositional",
        node_id=TUTORIAL_NODE,
    )


def test_a_withdrawn_explainer_lets_its_path_go(both: Harness) -> None:
    """F-D9 itself: filed; another request at the same path refused minutes later for the open
    pull request, named, not for a second; withdrawn; and the identical text filed again three
    minutes on. (The second request carries other text, so the duplicate rule's own two-minute
    slot, which is about text, not paths, does not answer first.)"""
    alice = both.token_for("code_alice", "alice")
    both.token_for("code_bob", "bob")
    first = explainer(both)
    both.clock.advance(seconds=300)
    with pytest.raises(ApiError) as caught:
        explainer(both, "bob", "Other words.\n")
    assert caught.value.code == appends.NAME_ERROR
    assert (caught.value.details or {})["pr_number"] == first["pr_number"]
    assert "this second" not in caught.value.message
    gone = both.client.delete(f"/submissions/{first['id']}", headers=both.auth(alice))
    assert gone.status_code == 200, gone.text
    both.clock.advance(seconds=180)
    again = explainer(both)
    assert again["path"] == first["path"] and again["pr_number"] != first["pr_number"]
    assert len(both.githost.pulls) == 2


def test_a_filed_record_does_not_hold_the_window_against_itself(both: Harness) -> None:
    """The in-flight hold covers the opening, not the window: once the record is in the store,
    the counter is dropped, and the open record is what holds the path (and names itself)."""
    alice = both.token_for("code_alice", "alice")
    first = annex(both, alice)
    assert first.status_code == 201
    ctx, path = both.context, first.json()["path"]
    later = ctx.clock.now() + timedelta(seconds=60)
    assert ctx.store.bump_counter(appends.name_key(ctx, path), later, by=0) == 0
    assert appends.path_holder(ctx, path) is not None
    with pytest.raises(ApiError) as caught, appends.holding_name(ctx, path=path):
        pass
    assert (caught.value.details or {})["pr_number"] == first.json()["pr_number"]


def test_an_abandoned_hold_lapses_with_its_window(both: Harness) -> None:
    """A process that dies mid-opening never drops its counter; the window lets the path go."""
    path = "targets/t/nodes/n/annex/abc.md"
    ctx = both.context
    ctx.store.bump_counter(appends.name_key(ctx, path), ctx.clock.now() + timedelta(seconds=60))
    with pytest.raises(ApiError) as caught, appends.holding_name(ctx, path=path):
        pass
    assert caught.value.code == appends.NAME_ERROR
    both.clock.advance(seconds=2 * appends.NAME_HOLD_S + 1)
    with appends.holding_name(ctx, path=path):
        pass


def test_two_requests_opening_together_are_one(both: Harness) -> None:
    """In flight: while one request is opening at a path, a second at the same path is refused
    and nothing of the second is held."""
    path = "targets/t/nodes/n/annex/abc.md"
    ctx = both.context
    with appends.holding_name(ctx, path=path):
        with pytest.raises(ApiError) as caught, appends.holding_name(ctx, path=path):
            pass
        assert caught.value.code == appends.NAME_ERROR
        assert "this second" not in caught.value.message


# --- a numbered path: stewards/<n>.yaml -----------------------------------------------------------


def test_an_open_steward_record_holds_its_number_naming_its_pull_request(h: Harness) -> None:  # noqa: F811
    """``stewards.next_number`` reads ``main`` only, so two open records take one number; the
    open one holds it, named, for as long as it is open, and the refusal says why in terms of
    the number, not of a second."""
    first = post(h, sign_in(h, "code_carol"))
    assert first.status_code == 201, first.text
    h.clock.advance(seconds=600)  # long past any window: only the open pull request holds it
    alice = sign_in(h, "code_alice")
    second = post(h, alice, name="Alice A.")
    assert second.status_code == 409, second.text
    doc = second.json()
    assert doc["error"] == "record-name-taken"
    assert doc["details"]["path"] == first.json()["path"]
    assert doc["details"]["pr_number"] == first.json()["pr_number"]
    assert "this second" not in doc["message"] and "Retry-After" not in second.headers
    assert f"#{first.json()['pr_number']}" in doc["message"]
    assert len(h.githost.pulls) == 1


def test_a_withdrawn_steward_record_lets_its_number_go(h: Harness) -> None:  # noqa: F811
    carol = sign_in(h, "code_carol")
    first = post(h, carol)
    assert first.status_code == 201, first.text
    alice = sign_in(h, "code_alice")
    assert post(h, alice, name="Alice A.").status_code == 409
    number = first.json()["pr_number"]
    bearer = h.token_for("code_carol", "carol")  # the same identity, as a token: DELETE takes one
    gone = h.client.delete(f"/submissions/{number:06d}", headers=h.auth(bearer))
    assert gone.status_code == 200, gone.text
    again = post(h, alice, name="Alice A.")
    assert again.status_code == 201, again.text
    assert again.json()["path"] == first.json()["path"]
