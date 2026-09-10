"""Revision-request and defect-claim refusals not yet named by a test (F08-R6, R7; D-16; C7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api_fakes import TUTORIAL_NODE, Harness

from opn_api import proposals

TARGET = "propositional"
STATEMENT_PATH = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/Statement.lean"
FIXTURE_GRAPH = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "graphs"
STATEMENT = (FIXTURE_GRAPH / "propositional" / STATEMENT_PATH).read_text()
EXHIBIT = "example : True := trivial\n"


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def valid_claim() -> dict[str, Any]:
    return {"stmt_ref": TUTORIAL_NODE, "class": "junk-value", "line": 1, "exhibit": EXHIBIT}


def test_defect_claim_field_shapes(harness: Harness) -> None:
    """D-16 (1): each pre-triage rule is named by the first field that breaks it."""
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[STATEMENT_PATH] = STATEMENT.encode()
    for overrides, code in (
        ({"class": None}, "defect-class"),
        ({"class": ["junk-value"]}, "defect-class"),
        ({"class": "Junk-Value"}, "defect-class"),
        ({"stmt_ref": None}, "stmt-ref-missing"),
        ({"stmt_ref": ""}, "stmt-ref-missing"),
        ({"stmt_ref": 7}, "stmt-ref-missing"),
        ({"line": True}, "defect-line"),
        ({"line": 1.0}, "defect-line"),
        ({"line": -1}, "defect-line"),
        ({"exhibit": 7}, "exhibit-invalid"),
        ({"exhibit": "x" * (proposals.MAX_LEAN_BYTES + 1)}, "field-too-long"),
    ):
        r = post(harness, "/defect-claims", token, {**valid_claim(), **overrides})
        assert r.status_code == 400, (overrides, r.text)
        assert r.json()["error"] == code, (overrides, r.text)
    assert harness.githost.pushes == []


def test_defect_claim_when_the_statement_cannot_be_read_is_503(harness: Harness) -> None:
    """C7: the line check needs the file; an unreachable graph is an outage, not a bounce."""
    token = harness.token_for("code_alice", "alice")
    assert harness.client.get("/frontier.json").status_code == 200  # the node facts are cached
    harness.githost.unreachable = True
    r = post(harness, "/defect-claims", token, valid_claim())
    assert r.status_code == 503
    assert r.json()["error"] == "graph-unreachable"
    assert harness.githost.pushes == []


def test_defect_claim_line_counts_the_committed_file_not_the_exhibit(harness: Harness) -> None:
    """D-16 (1): ``line`` indexes the referenced Statement.lean; the exhibit's length is
    irrelevant, and the last line is in while one past it is out."""
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[STATEMENT_PATH] = STATEMENT.encode()
    count = len(STATEMENT.splitlines())
    long_exhibit = "\n".join(["-- line"] * (count + 50)) + "\n"
    last = post(harness, "/defect-claims", token, {**valid_claim(), "line": count})
    assert last.status_code == 201, last.text
    beyond = post(
        harness,
        "/defect-claims",
        token,
        {**valid_claim(), "line": count + 1, "exhibit": long_exhibit},
    )
    assert beyond.status_code == 400
    assert beyond.json()["error"] == "defect-line"


def test_defs_ref_for_an_unknown_target_is_404(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/defect-claims", token, {**valid_claim(), "stmt_ref": "nowhere/defs/X.lean"})
    assert r.status_code == 404
    assert r.json()["error"] == "target-unknown"


def test_revision_request_evidence_shapes(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    base = {"node_id": TUTORIAL_NODE, "defect_class": "vacuity"}
    for evidence, code in (
        (None, "evidence-invalid"),
        (7, "evidence-invalid"),
        (["text"], "evidence-invalid"),
        ({"text": 7}, "evidence-invalid"),
        ({"text": "   "}, "evidence-invalid"),
        ({"text": "t", "exhibit": 7}, "exhibit-invalid"),
        ({"text": "t", "exhibit": "   "}, "exhibit-missing"),
        ({"text": "t", "exhibit": "x" * (proposals.MAX_LEAN_BYTES + 1)}, "field-too-long"),
    ):
        r = post(harness, "/revision-requests", token, {**base, "evidence": evidence})
        assert r.status_code == 400, (evidence, r.text)
        assert r.json()["error"] == code, (evidence, r.text)
    assert harness.githost.pushes == []


def test_revision_request_class_is_checked_before_the_evidence(harness: Harness) -> None:
    """The first violation is the one named: a bad class with bad evidence says class."""
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/revision-requests",
        token,
        {"node_id": TUTORIAL_NODE, "defect_class": "typo", "evidence": 7},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "defect-class"


def test_records_never_carry_the_token_or_identity_id(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[STATEMENT_PATH] = STATEMENT.encode()
    assert post(harness, "/defect-claims", token, valid_claim()).status_code == 201
    assert (
        post(
            harness,
            "/revision-requests",
            token,
            {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": "prose"},
        ).status_code
        == 201
    )
    identity_id = next(iter(harness.store.identities))
    for push, pr in zip(harness.githost.pushes, harness.githost.pulls, strict=True):
        for text in (push.message, pr.body, *push.files.values()):
            assert token not in text
            assert identity_id not in text


def test_host_failure_on_each_record_route_is_502(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[STATEMENT_PATH] = STATEMENT.encode()
    harness.githost.app_failure = "POST /repos/g/git/refs returned 500"
    for route, body in (
        ("/defect-claims", valid_claim()),
        (
            "/revision-requests",
            {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": "prose"},
        ),
    ):
        r = post(harness, route, token, body)
        assert r.status_code == 502, (route, r.text)
        assert r.json()["error"] == "pull-request-failed"
    assert harness.githost.pulls == []
