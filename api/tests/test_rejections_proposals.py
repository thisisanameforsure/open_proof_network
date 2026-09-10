"""Proposal refusals not yet named by a test (F08-R3, R4, R5, Q14; C7)."""

from __future__ import annotations

import json
from typing import Any

import yaml
from api_fakes import TUTORIAL_NODE, Harness

from opn_api import proposals

TARGET = "propositional"
NODES = f"targets/{TARGET}/nodes/"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
STATEMENT = "theorem OpnProp.and_weaken : forall p q : Prop, p /\\ q -> p \\/ q := by\n  sorry\n"
WITNESS = "theorem witness : True := trivial\n"
DEP_STATEMENT = "theorem OpnProp.and_reassoc : True := by\n  sorry\n"
RELATION_PROOF = "theorem relation : True := trivial\n"
HOLE = "and-reassoc--h1"


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def add_hole(harness: Harness, *, cause: str | None = "witness-missing") -> None:
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != HOLE]
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "blocked" if cause else "ready",
            "cause": cause,
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)


def test_deps_shapes_and_cap(harness: Harness) -> None:
    """Q14 (iii): at most 20 deps, each a node id string; nothing is pushed on refusal."""
    token = harness.token_for("code_alice", "alice")
    ok = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    for deps in (
        [7],
        [""],
        [None],
        "and-reassoc",
        {"and-reassoc": 1},
        [f"d{i}" for i in range(21)],
    ):
        r = post(harness, "/proposals/speculative", token, {**ok, "deps": deps})
        assert r.status_code == 400, deps
        assert r.json()["error"] == "deps-invalid", deps
    assert harness.githost.pushes == []


def test_duplicate_deps_are_collapsed_not_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    r = post(
        harness,
        "/proposals/speculative",
        token,
        {
            "target_id": TARGET,
            "statement": STATEMENT,
            "witness": WITNESS,
            "deps": ["and-reassoc", "and-reassoc"],
        },
    )
    assert r.status_code == 201, r.text
    files = harness.githost.pushes[-1].files
    meta = yaml.safe_load(files[f"{NODES}{r.json()['node_id']}/META.yaml"])
    assert meta["deps"] == ["and-reassoc"]


def test_a_dep_whose_statement_cannot_be_read_is_503(harness: Harness) -> None:
    """C7: a dep listed in graph.json whose Statement.lean the graph does not serve is an
    outage the caller is told about, not a Context.lean built from nothing."""
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/proposals/speculative",
        token,
        {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "deps": ["and-reassoc"]},
    )
    assert r.status_code == 503
    assert r.json()["error"] == "graph-unreachable"
    assert harness.githost.pushes == []


def test_lean_file_fields_must_be_strings_under_the_cap(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    ok = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    for field, value, code in (
        ("witness", 7, "witness-invalid"),
        ("witness", ["x"], "witness-invalid"),
        ("witness", "x" * (proposals.MAX_LEAN_BYTES + 1), "field-too-long"),
        ("statement", {"text": STATEMENT}, "statement-invalid"),
        ("statement", None, "statement-missing"),
    ):
        r = post(harness, "/proposals/speculative", token, {**ok, field: value})
        assert r.status_code == 400, (field, code)
        assert r.json()["error"] == code, (field, r.text)
    assert harness.githost.pushes == []


def test_target_id_missing_or_wrong_type(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    for body in (
        {"statement": STATEMENT, "witness": WITNESS},
        {"target_id": "", "statement": STATEMENT, "witness": WITNESS},
        {"target_id": ["propositional"], "statement": STATEMENT, "witness": WITNESS},
    ):
        for route in ("/proposals/speculative", "/proposals/variant"):
            r = post(harness, route, token, body)
            assert r.status_code == 400, (route, body)
            assert r.json()["error"] == "target-id-missing", (route, r.text)


def test_variant_relation_proof_must_be_a_string(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    base = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, "relation": "partial"}
    r = post(harness, "/proposals/variant", token, {**base, "relation_proof": 7})
    assert r.status_code == 400
    assert r.json()["error"] == "relation_proof-invalid"
    r = post(
        harness,
        "/proposals/variant",
        token,
        {**base, "relation_proof": "x" * (proposals.MAX_LEAN_BYTES + 1)},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "field-too-long"
    assert harness.githost.pushes == []


def test_variant_relation_of_the_wrong_type_is_refused(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    base = {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS}
    for relation in (7, ["related"], "RESOLVES"):
        r = post(harness, "/proposals/variant", token, {**base, "relation": relation})
        assert r.status_code == 400, relation
        assert r.json()["error"] == "relation-invalid", relation


def test_witness_route_shapes(harness: Harness) -> None:
    """R5: the node is checked before the witness, and the witness must be a Lean file."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness)
    for body, code in (
        ({"witness": WITNESS}, "node-id-missing"),
        ({"node_id": 7, "witness": WITNESS}, "node-id-missing"),
        ({"node_id": HOLE}, "witness-missing"),
        ({"node_id": HOLE, "witness": ""}, "witness-missing"),
        ({"node_id": HOLE, "witness": 7}, "witness-invalid"),
        ({"node_id": HOLE, "witness": "x" * (proposals.MAX_LEAN_BYTES + 1)}, "field-too-long"),
    ):
        r = post(harness, "/proposals/witness", token, body)
        assert r.status_code == 400, (body, r.text)
        assert r.json()["error"] == code, (body, r.text)
    assert harness.githost.pushes == []


def test_witness_for_a_node_blocked_for_another_cause_is_refused(harness: Harness) -> None:
    """R5: only ``witness-missing`` opens the slot; a node blocked on a dep does not take one."""
    token = harness.token_for("code_alice", "alice")
    add_hole(harness, cause="dep-refuted")
    r = post(harness, "/proposals/witness", token, {"node_id": HOLE, "witness": WITNESS})
    assert r.status_code == 400
    assert r.json()["error"] == "witness-not-missing"
    assert "dep-refuted" not in r.json()["error"]


def test_host_failure_on_a_proposal_is_502_and_opens_nothing(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.app_failure = "POST /repos/g/git/trees returned 502"
    r = post(
        harness,
        "/proposals/speculative",
        token,
        {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS},
    )
    assert r.status_code == 502
    assert r.json()["error"] == "pull-request-failed"
    assert harness.githost.pulls == []


def test_a_refused_proposal_does_not_spend_the_daily_budget() -> None:
    """F08 §6: the identity-layer bound counts proposals that reach the host, not bad requests."""
    from api_fakes import make_harness  # noqa: PLC0415 — one use

    h = make_harness({"OPN_API_PROPOSALS_PER_DAY": "1"})
    token = h.token_for("code_alice", "alice")
    bad = {"target_id": TARGET, "statement": STATEMENT}
    for _ in range(3):
        assert post(h, "/proposals/speculative", token, bad).status_code == 400
    ok = {**bad, "witness": WITNESS}
    assert post(h, "/proposals/speculative", token, ok).status_code == 201
    assert post(h, "/proposals/speculative", token, ok).status_code == 429


def test_proposal_never_carries_the_token_or_identity_id(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(
        harness,
        "/proposals/speculative",
        token,
        {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS},
    )
    assert r.status_code == 201, r.text
    push = harness.githost.pushes[-1]
    pr = harness.githost.pulls[-1]
    identity_id = next(iter(harness.store.identities))
    for text in (push.message, pr.body, *push.files.values()):
        assert token not in text
        assert identity_id not in text
    assert TUTORIAL_NODE not in pr.body  # the body names the proposed node, nothing else
