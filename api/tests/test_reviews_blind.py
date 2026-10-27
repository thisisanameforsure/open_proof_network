"""F26-T10 / AC12: the blind rule on the service's reads (F26-R3; D-9, D-28 v3.39).

``GET /reviews/<t>`` and ``get_review`` show a caller the words, the definitions' names, the
cases, the questions and the derived state; until the caller's own candidate is on the record,
every candidate's Lean is withheld (``lean: null``, ``lean_withheld: "blind"``) — to an anonymous
caller, and to a bearer whose pseudonym authored none. Once their candidate is merged, every
candidate's Lean is shown. The graph itself is public (R3): this is the service's rule, and the
record's ``read_others`` is shown as the claim it is.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_glosses_route import TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_reviews_routes import (
    LEAN,
    OTHER_LEAN,
    PROPOSER,
    WORDS,
    candidate_id,
    harness_over,
    opening,
    question,
    seed_candidates,
    seed_review,
)

ROUTE = f"/reviews/{TARGET}"
MINE = "theorem OpnProp.mine : ∀ p q : Prop, p ∧ q → q ∧ p := fun _ _ h => ⟨h.2, h.1⟩\n"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    root = make_tree(tmp_path, keys)
    seed_review(root, opening(), questions=[("q-1.yaml", question(1))])
    seed_candidates(root, (LEAN, "alice"), (OTHER_LEAN, "bob"))
    return root


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness_over(tree, {})


def by_id(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in doc["candidates"]}


def assert_blind(doc: dict[str, Any]) -> None:
    assert doc["blind"] is True
    assert {c["id"] for c in doc["candidates"]} >= {candidate_id(LEAN), candidate_id(OTHER_LEAN)}
    for c in doc["candidates"]:
        assert c["lean"] is None and c["lean_withheld"] == "blind", c
        assert c["author"] and c["read_others"] is False  # the claim, shown as the record has it
    assert LEAN not in str(doc) and OTHER_LEAN not in str(doc)
    # what the blind caller is shown: the words, the cases, the concepts, the questions, the state
    assert doc["review"]["words"] == WORDS and doc["review"]["concepts"] == ["And"]
    assert doc["review"]["cases"][0]["kind"] == "small-value"
    assert [q["id"] for q in doc["questions"]] == ["q-1"]
    assert doc["state"]["state"] == "open" and doc["state"]["candidates"] >= 2


def test_an_anonymous_read_withholds_every_candidates_lean(h: Harness) -> None:
    r = h.client.get(ROUTE)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["target_id"] == TARGET and doc["read_at"]
    assert_blind(doc)
    assert doc["caller"] is None


def test_a_bearer_with_no_candidate_is_blind_too(h: Harness) -> None:
    token = h.token_for("code_carol", "carol-agent")
    doc = h.client.get(ROUTE, headers=h.auth(token)).json()
    assert_blind(doc)
    assert doc["caller"] == "carol-agent"


def test_a_candidates_author_sees_every_lean(h: Harness) -> None:
    token = h.token_for("code_alice", "alice")  # the pseudonym the record credits
    doc = h.client.get(ROUTE, headers=h.auth(token)).json()
    assert doc["blind"] is False
    cands = by_id(doc)
    assert cands[candidate_id(LEAN)]["lean"] == LEAN
    assert cands[candidate_id(OTHER_LEAN)]["lean"] == OTHER_LEAN
    assert all(c["lean_withheld"] is None for c in doc["candidates"])


def test_after_the_callers_candidate_merges_the_lean_is_shown(h: Harness, tree: Path) -> None:
    """AC12's second half: carol's candidate on the record, and every Lean is hers to read."""
    token = h.token_for("code_carol", "carol-agent")
    assert_blind(h.client.get(ROUTE, headers=h.auth(token)).json())
    seed_candidates(tree, (MINE, "carol-agent"))
    serve_tree(h, tree)
    doc = h.client.get(ROUTE, headers=h.auth(token)).json()
    assert doc["blind"] is False
    cands = by_id(doc)
    assert cands[candidate_id(MINE)]["lean"] == MINE
    assert cands[candidate_id(LEAN)]["lean"] == LEAN
    # a pull request of theirs still open does not count: the record, not the proposal (Q3)
    other = h.token_for("code_bob", "bob-agent")
    sent = h.client.post(
        f"{ROUTE}/candidates",
        json={"lean": "theorem OpnProp.b : True := by\n  sorry\n", "read_others": False},
        headers=h.auth(other),
    )
    assert sent.status_code == 201, sent.text
    assert_blind(h.client.get(ROUTE, headers=h.auth(other)).json())


def test_a_bad_bearer_is_refused_rather_than_read_blind(h: Harness) -> None:
    r = h.client.get(ROUTE, headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


def test_get_review_holds_the_same_rule(h: Harness, tree: Path) -> None:
    client = McpClient(h)
    anonymous = client.ok("get_review", {"target_id": TARGET})
    assert_blind(anonymous)
    assert "untrusted_note" in anonymous
    carol = h.token_for("code_carol", "carol-agent")
    assert_blind(client.ok("get_review", {"target_id": TARGET}, token=carol))
    alice = h.token_for("code_alice", "alice")
    shown = client.ok("get_review", {"target_id": TARGET}, token=alice)
    assert shown["blind"] is False and by_id(shown)[candidate_id(LEAN)]["lean"] == LEAN
    seed_candidates(tree, (MINE, "carol-agent"))
    serve_tree(h, tree)
    mine = client.ok("get_review", {"target_id": TARGET}, token=carol)
    assert mine["blind"] is False and by_id(mine)[candidate_id(MINE)]["lean"] == MINE


def test_the_questions_read_is_open_and_carries_no_lean(h: Harness) -> None:
    r = h.client.get(f"{ROUTE}/questions")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["count"] == 1 and doc["questions"][0]["id"] == "q-1"
    assert "lean" not in str(doc).lower().replace("review", "")


def test_a_target_without_a_review_is_404(h: Harness, tree: Path) -> None:
    (tree / "targets" / TARGET / "review" / "review.yaml").unlink()
    h.githost.files.pop(f"targets/{TARGET}/review/review.yaml")
    h.context.files.clear()
    r = h.client.get(ROUTE)
    assert r.status_code == 404 and r.json()["error"] == "review-unknown"
    assert McpClient(h).failed("get_review", {"target_id": TARGET})["error"] == "review-unknown"
    assert h.client.get("/reviews/no-such").status_code == 404
    assert h.client.get("/reviews/no-such").json()["error"] == "target-unknown"


def test_the_review_includes_pairs_answers_and_signatures_as_the_record_holds_them(
    h: Harness, tree: Path
) -> None:
    a, b = sorted((candidate_id(LEAN), candidate_id(OTHER_LEAN)))
    pair = {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "forward": {"state": "proved", "exhibit": "e-deadbeef", "attempt": None},
        "backward": {"state": "open", "exhibit": None, "attempt": None},
        "date": "2026-09-05",
    }
    signature = {
        "schema": "review-signature/v1",
        "target": TARGET,
        "role": "intent",
        "decision": "accept",
        "cluster": a,
        "question": None,
        "date": "2026-09-06",
        "login": PROPOSER,
        "via": "approval-key",
        "key": "ssh-ed25519 AAAA",
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n",
    }
    seed_review(
        tree,
        opening(),
        questions=[("q-1.yaml", question(1))],
        pairs=[(f"{a}--{b}.yaml", pair)],
        signatures=[("intent-2026-09-06-1.yaml", signature)],
    )
    serve_tree(h, tree)
    doc = h.client.get(ROUTE).json()
    assert doc["pairs"][0]["a"] == a
    # F26-T19: each open direction carries its templates too; to this anonymous caller, withheld
    assert [(r["a"], r["b"], r["direction"]) for r in doc["open_pairs"]] == [(a, b, "backward")]
    assert doc["open_pairs"][0]["template_withheld"] == "blind"
    assert doc["signatures"][0]["login"] == PROPOSER
    assert doc["state"]["signers"] == {"intent": PROPOSER, "independent": None}
    assert doc["state"]["open_pairs"] == 1 and doc["answers"] == []
