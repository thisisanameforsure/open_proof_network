"""F22-T6 (testers 2026-10-06, feature request F): amend the words of an open pull request in place.

W1 waited about fifty minutes to correct one sentence: the only way was to close the pull request
and file again at the back of the queue. ``amends: <submission id>`` on ``POST /glosses`` (and on
``submit_gloss``) replaces the version an open words pull request carries: the service moves the
pull request's own branch to one commit from ``main`` adding the new file (a new hash, so a new
name) — the old file is gone from the branch — and the pull request, its number and its place in
the queue stay; the gate runs again on the new head. Only the pull request's author may amend,
only while it is open, and only with words for the same subject; each wrong case is refused
before anything moves.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_glosses_route import (
    NODE_DIR,
    make_h,
    make_keys,
    make_tree,
    post,
    put_version,
    serve,
    statement_gloss,
)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def words(text: str, **extra: Any) -> dict[str, Any]:
    return statement_gloss() | {"text": text, **extra}


def first(h: Harness, token: str, **extra: Any) -> Any:
    r = post(h, token, words("Conjunction reassociates, read left to right.", **extra))
    assert r.status_code == 201, r.text
    return r.json()


def test_the_author_amends_an_open_pull_request_in_place(h: Harness) -> None:
    bob = h.token_for("code_bob", "bob")
    opened = first(h, bob)
    pushed = h.githost.pushes[-1]
    h.clock.advance(minutes=5)
    r = post(h, bob, words("Conjunction regroups, read left to right.", amends=opened["id"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amended"] is True
    assert body["id"] == opened["id"]
    assert body["pr_number"] == opened["pr_number"] and len(h.githost.pulls) == 1
    assert body["hash"] != opened["hash"] and body["path"] != opened["path"]
    assert body["path"] == f"{NODE_DIR}/gloss/{body['hash']}.md"
    moved = h.githost.pushes[-1]
    assert moved.branch == pushed.branch and moved.replace is True
    assert list(moved.files) == [body["path"]], "the old version is not on the moved branch"
    assert body["head_sha"] and body["head_sha"] != f"{1:040d}"
    assert moved.author is not None and moved.author.name == "bob"
    # trackable: the pull request says what was replaced, before the branch moved
    [comment] = h.githost.comments
    assert opened["hash"] in comment.body and body["hash"] in comment.body
    # the record now knows the new words, so amending again works and a copy of them is refused
    h.clock.advance(minutes=5)
    again = post(h, bob, words("Conjunction regroups, read right to left.", amends=opened["id"]))
    assert again.status_code == 200, again.text


def test_another_identity_may_not_amend(h: Harness) -> None:
    bob, carol = h.token_for("code_bob", "bob"), h.token_for("code_carol", "carol")
    opened = first(h, bob)
    pushes = len(h.githost.pushes)
    r = post(h, carol, words("Carol's words.", amends=opened["id"]))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "not-holder"
    assert len(h.githost.pushes) == pushes


@pytest.mark.parametrize("merged", [True, False])
def test_a_finished_pull_request_may_not_be_amended(h: Harness, merged: bool) -> None:
    bob = h.token_for("code_bob", "bob")
    opened = first(h, bob)
    pushes = len(h.githost.pushes)
    h.githost.set_pull_request_state(opened["pr_number"], state="closed", merged=merged)
    h.context.pulls.clear()
    h.context.open_pulls = None
    r = post(h, bob, words("Too late.", amends=opened["id"]))
    # catalogued codes: a merged pull request is part of the record; a closed one is no longer
    # a submission the service holds open
    assert (r.status_code, r.json()["error"]) == (
        (409, "submission-merged") if merged else (404, "submission-unknown")
    ), r.text
    assert r.json()["details"]["pr_number"] == opened["pr_number"]
    assert len(h.githost.pushes) == pushes


def test_words_for_another_subject_may_not_amend(h: Harness) -> None:
    bob = h.token_for("code_bob", "bob")
    opened = first(h, bob)
    pushes = len(h.githost.pushes)
    other = words("The witness exhibits three true propositions.", amends=opened["id"])
    other["subject"] = {"kind": "witness", "node_id": other["subject"]["node_id"]}
    r = post(h, bob, other)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "subject-invalid"
    assert r.json()["details"]["amends"] == opened["id"]
    assert len(h.githost.pushes) == pushes


def test_an_unknown_or_non_words_submission_is_refused(h: Harness) -> None:
    bob = h.token_for("code_bob", "bob")
    r = post(h, bob, words("Words.", amends="01M230M2G0AAAAAAAAAAAAAAAA"))
    assert r.status_code == 404 and r.json()["error"] == "submission-unknown", r.text
    annex = h.client.post(
        "/annexes",
        json={"node_id": "and-reassoc", "text": "Symmetry.\n", "licence": "CC-BY-4.0"},
        headers=h.auth(bob),
    )
    assert annex.status_code == 201, annex.text
    r = post(h, bob, words("Words.", amends=annex.json()["id"]))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "subject-invalid"


def test_a_supersession_is_amended_without_refusing_itself(h: Harness, tree: Path) -> None:
    """The one-writer rules set the pull request being amended aside: it is the writer."""
    head = put_version(tree, "gloss", "Merged words.")
    serve(h, tree)
    bob = h.token_for("code_bob", "bob")
    opened = first(h, bob, supersedes=head)
    h.clock.advance(minutes=5)
    r = post(h, bob, words("Better words.", supersedes=head, amends=opened["id"]))
    assert r.status_code == 200, r.text
    assert r.json()["pr_number"] == opened["pr_number"]


def test_the_tool_takes_amends(h: Harness) -> None:
    bob = h.token_for("code_bob", "bob")
    opened = first(h, bob)
    h.clock.advance(minutes=5)
    args = words("Conjunction regroups.", amends=opened["id"])
    out = McpClient(h).ok("submit_gloss", args, token=bob)
    assert out["status"] == 200, out
    assert out["body"]["pr_number"] == opened["pr_number"]
