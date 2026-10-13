"""F26-T11 / AC14: the App's notice of review questions and the ``/me/`` listing (F26-R15;
D-9 v3.39).

When questions wait that no notice has named, the App posts one comment per batch on the
review's tracking issue (or pull request) in the graph repository, @-mentioning the intent
signer, listing the questions in words and linking the review page; what a notice has named is
remembered in the service's store, never on the graph, so a second run with nothing new posts
nothing. The same questions are listed for the signer by ``GET /session`` (``reviews``), which
``/me/`` draws. Review records are seeded into the fixture tree and served from the fake host at
``main``, as ``test_reviews_routes.py`` seeds them.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_glosses_route import CURATOR, SIGNER, TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_reviews_routes import PROPOSER, STEWARD, harness_over, opening, put, question, seed_review
from test_web_session import SITE, sign_in, web_headers

from opn_api import review_notice, reviews
from opn_gate import steward

PAGE = f"{SITE}/problems/{TARGET}/review/"
Q1 = "Suppose p were always false. Would the conjecture still be meant to hold?"
Q2 = "Is the conjecture meant for propositions only, or for any two statements?"
Q3 = "Should p and q be allowed to be the same proposition?"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The propositional fixture: alice an active steward, the owner a curator."""
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness_over(tree, {})


def two_waiting(tree: Path, head: dict[str, Any]) -> None:
    seed_review(
        tree,
        head,
        questions=[("q-1.yaml", question(1, question=Q1)), ("q-2.yaml", question(2, question=Q2))],
    )


def no_steward(h: Harness, tree: Path) -> None:
    """The target with its steward records gone, from the tree and from the fake host."""
    prefix = f"targets/{TARGET}/{steward.DIR}/"
    shutil.rmtree(tree / prefix)
    for path in [p for p in h.githost.files if p.startswith(prefix)]:
        del h.githost.files[path]


def tracked(**over: Any) -> dict[str, Any]:
    """A proposer's review (carol's) with a tracking issue."""
    return opening(tracking="issue:7", **over)


def run(h: Harness) -> list[dict[str, Any]]:
    return review_notice.run(h.context)


# --- AC14: one comment per batch ------------------------------------------------------------------


def test_two_waiting_questions_make_one_comment_naming_the_signer_both_and_the_page(
    h: Harness, tree: Path
) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    run(h)
    assert len(h.githost.comments) == 1
    c = h.githost.comments[0]
    assert c.repo == h.settings.graph_repo and c.number == 7
    assert f"@{PROPOSER}" in c.body
    assert Q1 in c.body and Q2 in c.body
    assert PAGE in c.body
    assert h.store.review_notified(TARGET) == {"q-1", "q-2"}


def test_a_second_run_with_no_new_question_posts_nothing(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    run(h)
    run(h)
    assert len(h.githost.comments) == 1


def test_a_third_question_makes_one_comment_naming_only_it(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    run(h)
    put(tree, "questions/q-3.yaml", question(3, question=Q3))
    serve_tree(h, tree)
    run(h)
    assert len(h.githost.comments) == 2
    body = h.githost.comments[1].body
    assert Q3 in body and Q1 not in body and Q2 not in body
    assert f"@{PROPOSER}" in body and PAGE in body


def test_an_answered_question_is_not_named(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    put(tree, "answers/a-1.yaml", {"schema": "review-answer/v1", "question": "q-1"})
    serve_tree(h, tree)
    run(h)
    assert len(h.githost.comments) == 1
    body = h.githost.comments[0].body
    assert Q2 in body and Q1 not in body


def test_a_pull_request_tracking_posts_on_that_pull_request(h: Harness, tree: Path) -> None:
    two_waiting(tree, opening(tracking="pr:12"))
    serve_tree(h, tree)
    run(h)
    assert [c.number for c in h.githost.comments] == [12]
    assert [c.kind for c in h.githost.comments] == ["pull"]


def test_an_issue_tracking_posts_as_an_issue_comment(h: Harness, tree: Path) -> None:
    """F26-Q17: a plain issue takes the comment through the issues permission, never the pull
    requests one (which GitHub refuses on an issue)."""
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    run(h)
    assert [(c.number, c.kind) for c in h.githost.comments] == [(7, "issue")]


def test_a_review_with_no_tracking_posts_nothing_and_says_why(
    h: Harness, tree: Path, caplog: pytest.LogCaptureFixture
) -> None:
    two_waiting(tree, opening())  # tracking: null
    serve_tree(h, tree)
    with caplog.at_level(logging.INFO, logger="opn_api"):
        out = run(h)
    assert h.githost.comments == []
    assert h.store.review_notified(TARGET) == set()
    assert any("tracking" in r.getMessage() and TARGET in r.getMessage() for r in caplog.records)
    assert [(o["target"], o["posted"], o["reason"]) for o in out] == [
        (TARGET, False, "no-tracking")
    ]


def test_a_tracking_value_that_names_no_issue_posts_nothing(h: Harness, tree: Path) -> None:
    two_waiting(tree, opening(tracking="issue:seven"))
    serve_tree(h, tree)
    out = run(h)
    assert h.githost.comments == []
    assert out[0]["reason"] == "tracking-unreadable"


def test_a_network_review_mentions_every_active_steward(
    h: Harness, tree: Path, keys: dict[str, Path]
) -> None:
    steward.write(
        tree / "targets" / TARGET,
        action=steward.COMMIT,
        login="bob",
        name="Bob",
        link="https://orcid.org/0000-0002-1825-0097",
        date="2026-10-05",
        key_path=keys[CURATOR],
        signer=SIGNER,
    )
    two_waiting(tree, opening(role="network", identity="network", tracking="issue:7"))
    serve_tree(h, tree)
    run(h)
    assert len(h.githost.comments) == 1
    body = h.githost.comments[0].body
    assert f"@{STEWARD}" in body and "@bob" in body
    assert body.count(f"@{STEWARD}") == 1 and body.count("@bob") == 1


def test_a_network_review_with_no_steward_posts_nothing(h: Harness, tree: Path) -> None:
    no_steward(h, tree)
    two_waiting(tree, opening(role="network", identity="network", tracking="issue:7"))
    serve_tree(h, tree)
    out = run(h)
    assert h.githost.comments == []
    assert h.store.review_notified(TARGET) == set()
    assert out[0]["reason"] == "no-intent-signer"


def test_every_login_named_is_one_the_answer_route_accepts(h: Harness, tree: Path) -> None:
    """The notice and ``POST /reviews/<t>/answers`` must agree on who the intent signer is."""
    for head in (tracked(), opening(role="network", identity="network", tracking="issue:7")):
        logins = review_notice.intent_signers(h.context, TARGET, head)
        assert logins
        assert all(reviews.intent_signer_holds(h.context, TARGET, head, x) for x in logins)


def test_a_failed_post_is_not_remembered_and_the_next_run_posts(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    h.githost.comment_failure = "host down"
    out = run(h)
    assert h.githost.comments == [] and out[0]["reason"] == "host-refused"
    assert h.store.review_notified(TARGET) == set()
    h.githost.comment_failure = None
    run(h)
    assert len(h.githost.comments) == 1


def test_the_module_entry_point_runs_once_and_prints_the_outcomes(
    h: Harness, tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    assert review_notice.main([TARGET], ctx=h.context) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == [
        {"target": TARGET, "posted": True, "reason": "posted", "questions": ["q-1", "q-2"]}
    ]
    assert len(h.githost.comments) == 1


def test_a_target_with_no_review_is_not_read_further(h: Harness, tree: Path) -> None:
    serve_tree(h, tree)
    assert run(h) == []
    assert h.githost.comments == []


def test_a_mention_inside_a_question_does_not_ping(h: Harness, tree: Path) -> None:
    seed_review(tree, tracked(), questions=[("q-1.yaml", question(1, question="Ask @mallory?"))])
    serve_tree(h, tree)
    run(h)
    body = h.githost.comments[0].body
    assert "@mallory" not in body and "mallory" in body


# --- AC14: /me/ -----------------------------------------------------------------------------------


def session_reviews(h: Harness, code: str) -> list[dict[str, Any]]:
    r = h.client.get("/session", headers=web_headers(sign_in(h, code)))
    assert r.status_code == 200, r.text
    return list(r.json()["reviews"])


def test_the_signer_s_session_lists_the_waiting_questions(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    assert session_reviews(h, "code_carol") == [
        {"target": TARGET, "question": "q-1", "text": Q1, "page": f"/problems/{TARGET}/review/"},
        {"target": TARGET, "question": "q-2", "text": Q2, "page": f"/problems/{TARGET}/review/"},
    ]


def test_a_login_that_is_not_the_signer_sees_none(h: Harness, tree: Path) -> None:
    two_waiting(tree, tracked())
    serve_tree(h, tree)
    assert session_reviews(h, "code_alice") == []


def test_a_network_review_lists_for_its_steward(h: Harness, tree: Path) -> None:
    two_waiting(tree, opening(role="network", identity="network"))  # no tracking: /me/ still lists
    serve_tree(h, tree)
    assert [e["question"] for e in session_reviews(h, "code_alice")] == ["q-1", "q-2"]


def test_with_no_steward_the_listing_is_empty_for_everyone(h: Harness, tree: Path) -> None:
    no_steward(h, tree)
    two_waiting(tree, opening(role="network", identity="network", tracking="issue:7"))
    serve_tree(h, tree)
    for code in ("code_alice", "code_carol", "code_owner"):
        assert session_reviews(h, code) == []
