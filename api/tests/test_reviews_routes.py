"""F26-T10 / AC11: the review's write routes and the ``submit_candidate``,
``list_review_questions`` and ``list_open_pairs`` tools (F26-R14; D-9, D-28, D-35 v3.39).

Each write, called with its valid body, opens exactly one pull request carrying exactly the
record (the pushed files are read back through the published schema, and a signed one through
the gate's own verifier); each wrong role, the blind-rule omission, a second answer to a closed
question and a signature by a candidate's author are refused by name before any pull request
(F13-T21's rule). Review records are seeded into the fixture tree and served from the fake host
at ``main``, the way ``test_registrations.py`` seeds records.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import CURATOR, TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import auth, identity, pending
from opn_api.githost import GitHubUser, PullRequest
from opn_api.store import Identity
from opn_gate import paths, schemas, signed
from opn_gate.signer import SshKeygenSigner

REVIEW_DIR = f"targets/{TARGET}/review"
PROPOSER = "carol"
STEWARD = "alice"
DAY = "2026-09-09"  # the fake clock's day
WORDS = "For every pair of propositions, p and q implies q and p."
LEAN = "theorem OpnProp.cand : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n"
OTHER_LEAN = "theorem OpnProp.other : ∀ p q : Prop, p ∧ q → q := by\n  sorry\n"


def candidate_id(lean: str) -> str:
    return "c-" + hashlib.sha256(lean.encode("utf-8")).hexdigest()[:8]


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    key = tmp_path_factory.mktemp("approval") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "approval"],
        check=True,
    )
    return key.read_text(), key.with_suffix(".pub").read_text().strip()


# --- seeding the record ---------------------------------------------------------------------------


def opening(role: str = "proposer", identity: str = PROPOSER, **over: Any) -> dict[str, Any]:
    return {
        "schema": "review/v1",
        "target": TARGET,
        "opened_by": {"identity": identity, "role": role},
        "date": "2026-09-01",
        "words": WORDS,
        "cases": [{"kind": "small-value", "text": "p = q = True gives True."}],
        "concepts": ["And"],
        "source": {"kind": "proposal", "ref": "pr:12"},
        "tracking": None,
        "supersedes": None,
    } | over


def candidate(lean: str, author: str, **over: Any) -> dict[str, Any]:
    cid = candidate_id(lean)
    return {
        "schema": "candidate/v1",
        "target": TARGET,
        "id": cid,
        "author": author,
        "method": "manual",
        "models": [],
        "read_others": False,
        "origin": "submitted",
        "source": None,
        "lean_file": f"{cid}.lean",
        "statement_hash": hashlib.sha256(lean.encode("utf-8")).hexdigest(),
        "date": "2026-09-02",
    } | over


def question(n: int = 1, **over: Any) -> dict[str, Any]:
    return {
        "schema": "review-question/v1",
        "target": TARGET,
        "id": f"q-{n}",
        "question": "Suppose p were always false. Would the conjecture still be meant to hold?",
        "raised_by": {"kind": "mutant", "ref": "e-deadbeef"},
        "asked_to": "intent",
        "date": "2026-09-03",
    } | over


def put(tree: Path, rel: str, doc: dict[str, Any] | str) -> None:
    path = tree / REVIEW_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = doc if isinstance(doc, str) else yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")


def seed_review(tree: Path, head: dict[str, Any] | None = None, **records: Any) -> None:
    """``review.yaml`` plus any ``candidates``, ``questions``, ``answers``, ``pairs`` or
    ``signatures`` given as lists of (name, document) or (name, text)."""
    put(tree, "review.yaml", head or opening())
    for sub, items in records.items():
        for name, doc in items:
            put(tree, f"{sub}/{name}", doc)


def seed_candidates(tree: Path, *cands: tuple[str, str]) -> None:
    """(lean, author) pairs, each as its record and its Lean file."""
    for lean, author in cands:
        cid = candidate_id(lean)
        put(tree, f"candidates/{cid}.yaml", candidate(lean, author))
        put(tree, f"candidates/{cid}.lean", lean)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The propositional fixture: alice a steward, the owner a curator, nobody else anything."""
    return make_tree(tmp_path, keys)


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser(PROPOSER, 1003, "2019-01-01T00:00:00Z")
    serve_tree(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


def web_post(h: Harness, cookie: str, route: str, doc: dict[str, Any]) -> Any:
    return h.client.post(route, json=doc, headers=web_headers(cookie))


def nothing_opened(h: Harness) -> None:
    assert h.githost.pushes == [] and h.githost.pulls == []


def landed(h: Harness, tree: Path, response: Any, schema: str) -> dict[str, Any]:
    """Exactly one pull request, one push, whose record (at the receipt's path) validates
    against its schema under the role the path locator gives it."""
    assert response.status_code == 201, response.text
    assert len(h.githost.pulls) == 1 and len(h.githost.pushes) == 1
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    assert path in push.files
    located = paths.locate(path)
    assert located is not None and schema in paths.SCHEMAS_FOR_ROLE[located.role], path
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    for name, content in push.files.items():
        dest = over / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    doc = dict(schemas.load_yaml(over / path, schema))
    assert doc["target"] == TARGET
    return doc


# --- POST /reviews (the opening) ------------------------------------------------------------------


OPEN_BODY: dict[str, Any] = {
    "target_id": TARGET,
    "words": WORDS,
    "cases": [{"kind": "small-value", "text": "p = q = True gives True."}],
    "concepts": ["And"],
}


def test_a_curator_session_opens_a_review_on_a_review_branch(h: Harness, tree: Path) -> None:
    r = web_post(h, sign_in(h, "code_owner"), "/reviews", OPEN_BODY)
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("review/"), "a curator's branch, which the actor leaves alone"
    assert out["path"] == f"{REVIEW_DIR}/review.yaml"
    doc = landed(h, tree, r, "review/v1")
    assert list(h.githost.pushes[-1].files) == [out["path"]]
    assert doc["opened_by"] == {"identity": CURATOR, "role": "curator"}
    assert (doc["date"], doc["words"], doc["concepts"]) == (DAY, WORDS, ["And"])
    assert doc["cases"] == OPEN_BODY["cases"]
    assert doc["source"] == {"kind": "proposal", "ref": None}
    assert doc["tracking"] is None and doc["supersedes"] is None
    (pr,) = h.githost.pulls
    assert pr.title == f"review: open {TARGET} by {CURATOR}"


def test_a_steward_bearer_opens_as_steward(h: Harness, tree: Path) -> None:
    token = h.token_for("code_alice", "alice-agent")  # the pseudonym is not the login
    r = h.client.post("/reviews", json=OPEN_BODY, headers=h.auth(token))
    doc = landed(h, tree, r, "review/v1")
    assert doc["opened_by"] == {"identity": STEWARD, "role": "steward"}


def test_a_proposer_opens_when_the_body_says_so_and_the_target_has_no_review(
    h: Harness, tree: Path
) -> None:
    body = {**OPEN_BODY, "role": "proposer", "source": {"kind": "proposal", "ref": "pr:12"}}
    r = web_post(h, sign_in(h, "code_carol"), "/reviews", body)
    doc = landed(h, tree, r, "review/v1")
    assert doc["opened_by"] == {"identity": PROPOSER, "role": "proposer"}
    assert doc["source"] == {"kind": "proposal", "ref": "pr:12"}


def test_a_login_with_no_role_is_refused_before_anything_opens(h: Harness) -> None:
    r = web_post(h, sign_in(h, "code_carol"), "/reviews", OPEN_BODY)
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "review-opener-not-allowed"
    nothing_opened(h)


def test_a_claimed_role_the_login_does_not_hold_is_refused(h: Harness) -> None:
    r = web_post(h, sign_in(h, "code_carol"), "/reviews", {**OPEN_BODY, "role": "curator"})
    assert r.status_code == 403 and r.json()["error"] == "review-opener-not-allowed"
    nothing_opened(h)


def test_policy_json_decides_who_may_open(tree: Path, approval: tuple[str, str]) -> None:
    """AC10's service half: with review_openers set to curators only, a steward's opening is
    refused review-opener-not-allowed and a curator's lands."""

    def setting(value: Any) -> dict[str, Any]:
        return {"value": value, "since": "2026-10-08", "reason": "a test"}

    doc = {
        "schema": "policy/v4",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "open",
        "panel": {
            "vote_threshold": setting({"numerator": 1, "denominator": 2}),
            "vote_window_days": setting(14),
            "vote_minimum": setting(2),
            "vote_minimum_from": setting(3),
            "steward_cap": setting(10),
            "steward_lapse_days": setting(183),
        },
        "review_openers": {
            "roles": ["curator"],
            "since": "2026-09-01",
            "evidence": "the first review",
        },
    }
    (tree / "policy.json").write_bytes(schemas.canonical_json(schemas.validate(doc, "policy/v4")))
    for h in harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]}):
        token = h.token_for("code_alice", "alice-agent")
        r = h.client.post("/reviews", json=OPEN_BODY, headers=h.auth(token))
        assert r.status_code == 403 and r.json()["error"] == "review-opener-not-allowed"
        assert r.json()["details"]["allowed"] == ["curator"]
        nothing_opened(h)
        ok = web_post(h, sign_in(h, "code_owner"), "/reviews", OPEN_BODY)
        assert ok.status_code == 201, ok.text


def test_a_target_that_has_a_review_is_refused_review_exists(h: Harness, tree: Path) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_owner"), "/reviews", OPEN_BODY)
    assert r.status_code == 409 and r.json()["error"] == "review-exists"
    nothing_opened(h)


def test_a_review_already_proposed_is_refused_review_exists(h: Harness) -> None:
    owner = sign_in(h, "code_owner")
    assert web_post(h, owner, "/reviews", OPEN_BODY).status_code == 201
    h.clock.advance(seconds=90)
    again = web_post(h, owner, "/reviews", {**OPEN_BODY, "words": "Other words."})
    assert again.status_code == 409 and again.json()["error"] == "review-exists"
    assert again.json()["details"]["pr_number"] == 1
    assert len(h.githost.pulls) == 1


def test_a_tutorial_identity_has_no_login_to_open_with(h: Harness) -> None:
    held = Identity(
        "01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z", identity.DCO_VERSION
    )
    h.store.put_identity(held)
    raw, _ = auth.new_session(h.context, held.id)
    r = web_post(h, raw, "/reviews", OPEN_BODY)
    assert r.status_code == 403 and r.json()["error"] == "github-login-required"
    nothing_opened(h)


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"words": ""}, "arguments-invalid"),
        ({"words": 7}, "arguments-invalid"),
        ({"cases": "p = q"}, "arguments-invalid"),
        ({"cases": [{"kind": "guess", "text": "x"}]}, "record-invalid"),
        ({"concepts": ["not a name!"]}, "record-invalid"),
        ({"source": {"kind": "proposal"}}, "arguments-invalid"),
        ({"role": "network"}, "arguments-invalid"),
        ({"target_id": "no-such"}, "target-unknown"),
        ({"opened_by": {"identity": "x", "role": "curator"}}, "unknown-field"),
    ],
)
def test_bad_openings_are_refused_and_open_nothing(
    h: Harness, over: dict[str, Any], code: str
) -> None:
    r = web_post(h, sign_in(h, "code_owner"), "/reviews", {**OPEN_BODY, **over})
    assert r.status_code in (400, 404), (over, r.text)
    assert r.json()["error"] == code, (over, r.json())
    nothing_opened(h)


# --- POST /reviews/<t>/candidates -----------------------------------------------------------------


CANDIDATES = f"/reviews/{TARGET}/candidates"


def test_a_candidate_lands_as_its_record_and_its_lean_in_one_pull_request(
    h: Harness, tree: Path
) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    body = {"lean": LEAN, "models": [], "read_others": False}
    r = h.client.post(CANDIDATES, json=body, headers=h.auth(token))
    doc = landed(h, tree, r, "candidate/v1")
    cid = candidate_id(LEAN)
    out = r.json()
    assert out["branch"].startswith("append/"), "the merge actor takes append/ as it is"
    assert out["path"] == f"{REVIEW_DIR}/candidates/{cid}.yaml"
    push = h.githost.pushes[-1]
    assert sorted(push.files) == sorted([out["path"], f"{REVIEW_DIR}/candidates/{cid}.lean"])
    assert push.files[f"{REVIEW_DIR}/candidates/{cid}.lean"] == LEAN
    assert (doc["id"], doc["lean_file"], doc["author"]) == (cid, f"{cid}.lean", "alice-agent")
    assert doc["statement_hash"] == hashlib.sha256(LEAN.encode()).hexdigest()
    assert (doc["method"], doc["models"], doc["read_others"]) == ("manual", [], False)
    assert (doc["origin"], doc["source"], doc["date"]) == ("submitted", None, DAY)
    (pr,) = h.githost.pulls
    assert pr.title == f"candidate: {TARGET} {cid} by alice-agent"
    assert "blind" in pr.body


def test_a_models_candidate_takes_its_method_from_the_last_automation_declaration(
    h: Harness, tree: Path
) -> None:
    """R3: the submitter's automation method is what their last submission declared (D-23
    v3.37); with no declaration, a candidate naming models is `other` and one naming none is
    `manual`."""
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    named = {"lean": LEAN, "models": ["claude-fable-5-1"], "read_others": True}
    r = h.client.post(CANDIDATES, json=named, headers=h.auth(token))
    doc = landed(h, tree, r, "candidate/v1")
    assert (doc["method"], doc["models"], doc["read_others"]) == (
        "other",
        ["claude-fable-5-1"],
        True,
    )
    # now a declaration on the record: the identity's last submission said `agent`
    held = h.store.get_identity_by_pseudonym("alice-agent")
    assert held is not None
    pending.record(
        h.context,
        held,
        submission_id="01DECLARED",
        kind="proof",
        target_id=TARGET,
        node_id="and-reassoc",
        pr=PullRequest(99, "https://example/pr/99"),
        automation={"method": "agent", "models": ["claude-fable-5-1"], "framework": "Claude Code"},
    )
    h.clock.advance(seconds=90)
    r2 = h.client.post(CANDIDATES, json={**named, "lean": OTHER_LEAN}, headers=h.auth(token))
    assert r2.status_code == 201, r2.text
    doc2 = yaml.safe_load(h.githost.pushes[-1].files[r2.json()["path"]])
    assert doc2["method"] == "agent"


def test_read_others_must_be_declared_true_or_false(h: Harness, tree: Path) -> None:
    """R3's blind rule at the write: the declaration is a claim the record shows, and a candidate
    that makes none is refused candidate-not-blind before anything opens."""
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    for body in (
        {"lean": LEAN},
        {"lean": LEAN, "read_others": None},
        {"lean": LEAN, "read_others": "no"},
    ):
        r = h.client.post(CANDIDATES, json=body, headers=h.auth(token))
        assert r.status_code == 400, (body, r.text)
        assert r.json()["error"] == "candidate-not-blind", body
    nothing_opened(h)


def test_a_candidate_on_a_target_with_no_review_is_404(h: Harness) -> None:
    token = h.token_for("code_alice", "alice-agent")
    r = h.client.post(CANDIDATES, json={"lean": LEAN, "read_others": False}, headers=h.auth(token))
    assert r.status_code == 404 and r.json()["error"] == "review-unknown"
    nothing_opened(h)


def test_a_candidate_already_on_the_record_is_refused_by_its_id(h: Harness, tree: Path) -> None:
    seed_review(tree)
    seed_candidates(tree, (LEAN, "bob"))
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    r = h.client.post(CANDIDATES, json={"lean": LEAN, "read_others": False}, headers=h.auth(token))
    assert r.status_code == 409 and r.json()["error"] == "candidate-exists"
    assert r.json()["details"]["candidate"] == candidate_id(LEAN)
    nothing_opened(h)


def test_a_candidate_needs_a_bearer_not_a_web_session(h: Harness, tree: Path) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_owner"), CANDIDATES, {"lean": LEAN, "read_others": False})
    assert r.status_code == 401
    nothing_opened(h)


def test_three_candidates_a_day_per_identity_per_review(h: Harness, tree: Path) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    for i in range(3):
        body = {"lean": f"theorem OpnProp.c{i} : True := by\n  sorry\n", "read_others": False}
        assert h.client.post(CANDIDATES, json=body, headers=h.auth(token)).status_code == 201
        h.clock.advance(seconds=90)
    r = h.client.post(CANDIDATES, json={"lean": LEAN, "read_others": False}, headers=h.auth(token))
    assert r.status_code == 429 and r.json()["error"] == "rate-limited"
    assert len(h.githost.pulls) == 3


# --- POST /reviews/<t>/answers --------------------------------------------------------------------


ANSWERS = f"/reviews/{TARGET}/answers"
ANSWER = {
    "question": "q-1",
    "answer": "No: the conjecture is about both propositions.",
    "cites": None,
}


def test_the_proposer_answers_a_question_signed_by_the_approval_key(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_carol"), ANSWERS, ANSWER)
    doc = landed(h, tree, r, "review-answer/v1")
    assert r.json()["path"] == f"{REVIEW_DIR}/answers/a-1.yaml"
    assert list(h.githost.pushes[-1].files) == [r.json()["path"]]
    assert (doc["id"], doc["question"], doc["answer"], doc["cites"]) == (
        "a-1",
        "q-1",
        ANSWER["answer"],
        None,
    )
    assert (doc["login"], doc["via"], doc["date"]) == (PROPOSER, "approval-key", DAY)
    assert doc["key"].split()[:2] == approval[1].split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # the gate's own verifier


def test_a_steward_answers_for_a_network_opened_review(h: Harness, tree: Path) -> None:
    seed_review(tree, opening("network", "network"), questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_alice"), ANSWERS, {**ANSWER, "cites": "Euclid IX.20"})
    doc = landed(h, tree, r, "review-answer/v1")
    assert doc["login"] == STEWARD and doc["cites"] == "Euclid IX.20"


def test_answers_are_numbered_after_the_merged_and_the_open_ones(h: Harness, tree: Path) -> None:
    answered = {
        "schema": "review-answer/v1",
        "target": TARGET,
        "id": "a-3",
        "question": "q-7",
        "answer": "Yes.",
        "cites": None,
        "date": "2026-09-04",
        "login": PROPOSER,
        "via": "approval-key",
        "key": "ssh-ed25519 AAAA",
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n",
    }
    seed_review(
        tree,
        questions=[("q-1.yaml", question(1)), ("q-2.yaml", question(2)), ("q-7.yaml", question(7))],
        answers=[("a-3.yaml", answered)],
    )
    serve_tree(h, tree)
    carol = sign_in(h, "code_carol")
    first = web_post(h, carol, ANSWERS, ANSWER)
    assert first.status_code == 201 and first.json()["path"].endswith("a-4.yaml")
    h.clock.advance(seconds=90)
    second = web_post(h, carol, ANSWERS, {**ANSWER, "question": "q-2"})
    assert second.status_code == 201 and second.json()["path"].endswith("a-5.yaml")


def test_only_the_intent_signer_answers(h: Harness, tree: Path) -> None:
    """A proposer's review: the curator and the steward are not the intent signer."""
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    for code in ("code_owner", "code_alice"):
        r = web_post(h, sign_in(h, code), ANSWERS, ANSWER)
        assert r.status_code == 403, (code, r.text)
        assert r.json()["error"] == "review-not-intent-signer"
    nothing_opened(h)


def test_a_network_review_with_no_steward_has_no_intent_signer(h: Harness, tree: Path) -> None:
    """F26-Q5: the questions wait, and the refusal says the target needs a steward."""
    shutil.rmtree(tree / "targets" / TARGET / "stewards")
    seed_review(tree, opening("network", "network"), questions=[("q-1.yaml", question(1))])
    h.githost.files = {k: v for k, v in h.githost.files.items() if "/stewards/" not in k}
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_carol"), ANSWERS, ANSWER)
    assert r.status_code == 403 and r.json()["error"] == "review-not-intent-signer"
    assert "steward" in r.json()["message"]
    nothing_opened(h)


def test_an_unknown_question_is_404(h: Harness, tree: Path) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    r = web_post(h, sign_in(h, "code_carol"), ANSWERS, {**ANSWER, "question": "q-9"})
    assert r.status_code == 404 and r.json()["error"] == "review-question-unknown"
    nothing_opened(h)


def test_a_second_answer_to_an_answered_question_is_refused(h: Harness, tree: Path) -> None:
    """Merged or still open: once an answer names the question, a second is 409."""
    seed_review(tree, questions=[("q-1.yaml", question(1)), ("q-2.yaml", question(2))])
    serve_tree(h, tree)
    carol = sign_in(h, "code_carol")
    first = web_post(h, carol, ANSWERS, ANSWER)
    assert first.status_code == 201, first.text
    h.clock.advance(seconds=90)
    again = web_post(h, carol, ANSWERS, {**ANSWER, "answer": "Other words."})
    assert again.status_code == 409 and again.json()["error"] == "review-question-answered"
    assert again.json()["details"]["pr_number"] == 1
    # and one merged on the graph
    path = first.json()["path"]
    (tree / path).parent.mkdir(parents=True, exist_ok=True)
    (tree / path).write_text(h.githost.pushes[-1].files[path], encoding="utf-8")
    serve_tree(h, tree)
    h.githost.set_pull_request_state(
        1, state="closed", merged=True, merged_at="2026-09-09T12:01:00Z"
    )
    h.clock.advance(seconds=90)
    merged = web_post(h, carol, ANSWERS, {**ANSWER, "answer": "Third words."})
    assert merged.status_code == 409 and merged.json()["error"] == "review-question-answered"
    assert len(h.githost.pulls) == 1


def test_an_answer_needs_a_web_session(h: Harness, tree: Path) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    token = h.token_for("code_carol", "carol-agent")
    r = h.client.post(ANSWERS, json=ANSWER, headers=h.auth(token))
    assert r.status_code == 201, "a bearer with a GitHub login is the same person (F23-R3)"
    assert h.client.post(ANSWERS, json=ANSWER).status_code == 401


# --- POST /reviews/<t>/signatures -----------------------------------------------------------------


SIGNATURES = f"/reviews/{TARGET}/signatures"


def test_the_intent_signer_accepts_a_cluster(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    seed_review(tree)
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"role": "intent", "decision": "accept", "cluster": candidate_id(LEAN)}
    r = web_post(h, sign_in(h, "code_carol"), SIGNATURES, body)
    doc = landed(h, tree, r, "review-signature/v1")
    assert r.json()["path"] == f"{REVIEW_DIR}/signatures/intent-{DAY}-1.yaml"
    assert (doc["role"], doc["decision"], doc["cluster"], doc["question"]) == (
        "intent",
        "accept",
        candidate_id(LEAN),
        None,
    )
    assert (doc["login"], doc["via"]) == (PROPOSER, "approval-key")
    assert doc["key"].split()[:2] == approval[1].split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())


def test_an_independent_signer_wrote_no_candidate_and_is_not_the_intent_signer(
    h: Harness, tree: Path
) -> None:
    seed_review(tree)
    seed_candidates(tree, (LEAN, "alice"), (OTHER_LEAN, "bob"))
    serve_tree(h, tree)
    body = {"role": "independent", "decision": "accept", "cluster": candidate_id(LEAN)}
    r = web_post(h, sign_in(h, "code_owner"), SIGNATURES, body)
    doc = landed(h, tree, r, "review-signature/v1")
    assert doc["login"] == CURATOR and doc["role"] == "independent"
    assert r.json()["path"].endswith(f"independent-{DAY}-1.yaml")


def test_a_candidates_author_may_not_sign_as_independent(h: Harness, tree: Path) -> None:
    """R9: the author of the Lean, by pseudonym or by login, is never the independent signer."""
    seed_review(tree)
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"role": "independent", "decision": "accept", "cluster": candidate_id(LEAN)}
    r = web_post(h, sign_in(h, "code_alice"), SIGNATURES, body)
    assert r.status_code == 403 and r.json()["error"] == "review-signer-wrote-candidate"
    assert r.json()["details"]["candidates"] == [candidate_id(LEAN)]
    nothing_opened(h)


def test_the_intent_signer_may_not_sign_as_independent_nor_a_stranger_as_intent(
    h: Harness, tree: Path
) -> None:
    seed_review(tree)
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"decision": "accept", "cluster": candidate_id(LEAN)}
    r = web_post(h, sign_in(h, "code_carol"), SIGNATURES, {**body, "role": "independent"})
    assert r.status_code == 403 and r.json()["error"] == "review-not-signer"
    r = web_post(h, sign_in(h, "code_owner"), SIGNATURES, {**body, "role": "intent"})
    assert r.status_code == 403 and r.json()["error"] == "review-not-signer"
    nothing_opened(h)


def test_a_send_back_names_a_question_and_no_cluster(h: Harness, tree: Path) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"role": "intent", "decision": "send-back", "question": "q-1"}
    r = web_post(h, sign_in(h, "code_carol"), SIGNATURES, body)
    doc = landed(h, tree, r, "review-signature/v1")
    assert (doc["decision"], doc["cluster"], doc["question"]) == ("send-back", None, "q-1")


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"role": "network"}, "arguments-invalid"),
        ({"decision": "maybe"}, "arguments-invalid"),
        ({"cluster": None}, "arguments-invalid"),  # an accept names its cluster
        ({"cluster": "c-00000000"}, "candidate-unknown"),
        ({"decision": "send-back", "cluster": None, "question": "q-9"}, "review-question-unknown"),
    ],
)
def test_bad_signatures_are_refused_and_open_nothing(
    h: Harness, tree: Path, over: dict[str, Any], code: str
) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"role": "intent", "decision": "accept", "cluster": candidate_id(LEAN), **over}
    r = web_post(h, sign_in(h, "code_carol"), SIGNATURES, body)
    assert r.status_code in (400, 404), (over, r.text)
    assert r.json()["error"] == code, (over, r.json())
    nothing_opened(h)


def test_signatures_are_numbered_per_role_and_day(h: Harness, tree: Path) -> None:
    seed_review(tree)
    seed_candidates(tree, (LEAN, "alice"))
    serve_tree(h, tree)
    body = {"role": "intent", "decision": "accept", "cluster": candidate_id(LEAN)}
    carol = sign_in(h, "code_carol")
    first = web_post(h, carol, SIGNATURES, body)
    assert first.json()["path"].endswith(f"intent-{DAY}-1.yaml")
    h.clock.advance(seconds=90)
    second = web_post(h, carol, SIGNATURES, {**body, "decision": "split"})
    assert second.status_code == 201, second.text
    assert second.json()["path"].endswith(f"intent-{DAY}-2.yaml")
    other = web_post(h, sign_in(h, "code_owner"), SIGNATURES, {**body, "role": "independent"})
    # numbered after the two still open for the target: a gap costs nothing
    assert other.json()["path"].endswith(f"independent-{DAY}-3.yaml")


# --- the tools ------------------------------------------------------------------------------------


def test_submit_candidate_is_the_route_body_for_body(h: Harness, tree: Path) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    args = {"target_id": TARGET, "lean": LEAN, "models": ["m"], "read_others": False}
    out = McpClient(h).ok("submit_candidate", args, token=token)
    assert out["status"] == 201
    assert out["body"]["path"] == f"{REVIEW_DIR}/candidates/{candidate_id(LEAN)}.yaml"
    doc = yaml.safe_load(h.githost.pushes[-1].files[out["body"]["path"]])
    assert doc["author"] == "alice-agent" and doc["models"] == ["m"]


def test_submit_candidate_passes_the_blind_refusal_through(h: Harness, tree: Path) -> None:
    seed_review(tree)
    serve_tree(h, tree)
    token = h.token_for("code_alice", "alice-agent")
    out = McpClient(h).failed("submit_candidate", {"target_id": TARGET, "lean": LEAN}, token=token)
    assert out["status"] == 400 and out["body"]["error"] == "candidate-not-blind"
    nothing_opened(h)


def test_submit_candidate_needs_a_token(h: Harness) -> None:
    out = McpClient(h).failed("submit_candidate", {"target_id": TARGET, "lean": LEAN})
    assert out["status"] == 401 and "get_token" in json.dumps(out["body"])


def test_list_review_questions_lists_the_waiting_ones(h: Harness, tree: Path) -> None:
    answered = {
        "schema": "review-answer/v1",
        "target": TARGET,
        "id": "a-1",
        "question": "q-1",
        "answer": "Yes.",
        "cites": None,
        "date": "2026-09-04",
        "login": PROPOSER,
        "via": "approval-key",
        "key": "ssh-ed25519 AAAA",
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n",
    }
    seed_review(
        tree,
        questions=[("q-1.yaml", question(1)), ("q-2.yaml", question(2, question="Second?"))],
        answers=[("a-1.yaml", answered)],
    )
    serve_tree(h, tree)
    out = McpClient(h).ok("list_review_questions", {"target_id": TARGET})
    assert out["count"] == 1 and out["target_id"] == TARGET
    [row] = out["questions"]
    assert (row["target_id"], row["id"], row["asked_to"]) == (TARGET, "q-2", "intent")
    assert row["raised_by"] == {"kind": "mutant", "ref": "e-deadbeef"}
    assert "Second?" in json.dumps(row["question"])
    everything = McpClient(h).ok("list_review_questions", {})
    assert everything["count"] == 1 and everything["target_id"] is None
    assert McpClient(h).failed("list_review_questions", {"target_id": "no-such"})["error"] == (
        "not-found"
    )
    route = h.client.get(f"/reviews/{TARGET}/questions")
    assert route.status_code == 200 and route.json()["count"] == 1


def test_list_open_pairs_lists_each_open_direction(h: Harness, tree: Path) -> None:
    a, b = sorted((candidate_id(LEAN), candidate_id(OTHER_LEAN)))
    pair = {
        "schema": "pair/v1",
        "target": TARGET,
        "a": a,
        "b": b,
        "forward": {"state": "proved", "exhibit": "e-deadbeef", "attempt": None},
        "backward": {
            "state": "open",
            "exhibit": None,
            "attempt": {"who": "gate", "tool": "grind", "budget_s": 20},
        },
        "date": "2026-09-05",
    }
    seed_review(tree, pairs=[(f"{a}--{b}.yaml", pair)])
    serve_tree(h, tree)
    out = McpClient(h).ok("list_open_pairs", {"target_id": TARGET})
    assert out["count"] == 1
    [row] = out["pairs"]
    assert (row["target_id"], row["a"], row["b"], row["direction"]) == (TARGET, a, b, "backward")
    assert row["attempt"] == {"who": "gate", "tool": "grind", "budget_s": 20}
    assert row["submit_as"] == "pair-proof"
    assert McpClient(h).ok("list_open_pairs", {})["count"] == 1


def test_a_target_without_a_review_has_no_questions_and_no_pairs(h: Harness) -> None:
    assert McpClient(h).ok("list_review_questions", {"target_id": TARGET})["count"] == 0
    assert McpClient(h).ok("list_open_pairs", {})["count"] == 0
    assert h.client.get(f"/reviews/{TARGET}/questions").json()["count"] == 0


def test_the_submissions_are_watchable_under_their_kinds(h: Harness, tree: Path) -> None:
    seed_review(tree, questions=[("q-1.yaml", question(1))])
    serve_tree(h, tree)
    carol = sign_in(h, "code_carol")
    answer = web_post(h, carol, ANSWERS, ANSWER).json()
    r = h.client.get(f"/submissions/{answer['pr_number']}")
    assert r.status_code == 200 and r.json()["submission"]["kind"] == "review-answer"
    assert re.match(r"^append/", answer["branch"])
