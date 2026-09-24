"""Finding: the service could not file a circularity claim, nor say why a circular hole is closed.

Found live 2026-09-23 by the nine testers: ``erdos-1050--h1-v2--h1`` states the root again after a
reindexing identity and ``erdos-69--h2-v2--h1-v2--h4`` is equivalent to the target, and
``POST /defect-claims`` had no way to say so — the class list is D-16's eight, no field names the
statement the hole circles back to, and a claim naming ``other-with-exhibit`` would merge with an
exhibit that is only elaborated (``test_finding_circular_decomposition`` in the gate has the whole
account). The owner's ruling: a ``circular-decomposition`` claim names an ``ancestor`` (a node that
depends on the hole transitively) and carries an exhibit proving ``ancestor → hole``; the service
applies the mechanical half (the class, the exhibit's presence, the ancestor being an ancestor) and
the gate checks the exhibit's type in the sandbox. Once merged the hole leaves the frontier with the
cause ``circular``, and ``POST /claims`` says that rather than "ready and not on the frontier".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from api_fakes import Harness
from mcp_client import McpClient
from test_claims_defect import FIXTURE_GRAPH, gate_checks, only_file, post

from opn_api import claims
from opn_gate import paths, schemas

TARGET = "propositional"
HOLE = "and-reassoc"
ANCESTOR = "and-swap-reassoc"
SIBLING = "tutorial-and-swap"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
STATEMENT_PATH = f"targets/{TARGET}/nodes/{HOLE}/Statement.lean"
EXHIBIT = (
    "theorem circular :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) :=\n"
    "  fun _ _ _ _ h => ⟨h.1.1, h.1.2, h.2⟩\n"
)
VALID: dict[str, Any] = {
    "stmt_ref": HOLE,
    "class": "circular-decomposition",
    "ancestor": ANCESTOR,
    "line": 1,
    "exhibit": EXHIBIT,
}


def graph_rows(harness: Harness) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(harness.githost.files[GRAPH_PATH])["nodes"]
    return rows


def commit_graph(harness: Harness, rows: list[dict[str, Any]]) -> None:
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = rows
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)


def add_ancestor(harness: Harness) -> None:
    """The fixture graph's root, which depends on the hole, as the committed graph.json has it."""
    rows = graph_rows(harness)
    rows.append(
        {
            "node_id": ANCESTOR,
            "status": "blocked",
            "cause": None,
            "deps": [SIBLING, HOLE],
            "origin": "authored",
            "statement_hash": "3" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    commit_graph(harness, rows)
    harness.githost.files[STATEMENT_PATH] = (FIXTURE_GRAPH / TARGET / STATEMENT_PATH).read_bytes()


def test_a_circularity_claim_is_filed_at_v3_and_passes_the_gate(
    harness: Harness, tmp_path: Path
) -> None:
    add_ancestor(harness)
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/defect-claims", token, VALID)
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path.startswith(f"targets/{TARGET}/nodes/{HOLE}/defects/")
    doc = yaml.safe_load(content)
    assert doc["schema"] == "defect-claim/v3"
    assert (doc["class"], doc["ancestor"]) == ("circular-decomposition", ANCESTOR)
    assert doc["exhibit"] == EXHIBIT
    assert schemas.violations(doc, "defect-claim/v3") == []
    located = paths.locate(path)
    assert located is not None and located.role == "defect-claim"
    # The CI check on what landed: the ancestor, then the exhibit's type (fake: it matches).
    assert gate_checks(tmp_path, path, content) == []


def test_the_mcp_tool_files_the_same_claim(harness: Harness) -> None:
    """D-28: ``file_defect_claim`` is the route, so it carries ``ancestor`` through."""
    add_ancestor(harness)
    token = harness.token_for("code_alice", "alice")
    McpClient(harness).ok("file_defect_claim", VALID, token=token)
    _, content = only_file(harness)
    assert yaml.safe_load(content)["ancestor"] == ANCESTOR


def test_every_other_class_is_still_filed_at_v1(harness: Harness) -> None:
    """Guard: the service files v3 only for the class that needs it (D-34: v1 stays live)."""
    add_ancestor(harness)
    token = harness.token_for("code_alice", "alice")
    body = {k: v for k, v in VALID.items() if k != "ancestor"} | {"class": "junk-value"}
    assert post(harness, "/defect-claims", token, body).status_code == 201
    _, content = only_file(harness)
    assert yaml.safe_load(content)["schema"] == "defect-claim/v1"


def test_the_ancestor_is_required_and_must_be_above_the_hole(harness: Harness) -> None:
    add_ancestor(harness)
    token = harness.token_for("code_alice", "alice")
    for body, why in (
        ({k: v for k, v in VALID.items() if k != "ancestor"}, "no ancestor"),
        ({**VALID, "ancestor": SIBLING}, "a sibling, not above the hole"),
        ({**VALID, "ancestor": HOLE}, "the hole itself"),
        ({**VALID, "ancestor": "ghost"}, "not a node"),
        ({**VALID, "class": "junk-value"}, "an ancestor on another class"),
    ):
        r = post(harness, "/defect-claims", token, body)
        assert (r.status_code, r.json().get("error")) == (400, "circular-ancestor"), (why, r.text)
    sibling = post(harness, "/defect-claims", token, {**VALID, "ancestor": SIBLING})
    assert ANCESTOR in sibling.json()["message"], "the refusal names the ancestors there are"
    missing = post(
        harness, "/defect-claims", token, {k: v for k, v in VALID.items() if k != "exhibit"}
    )
    assert (missing.status_code, missing.json()["error"]) == (400, "exhibit-missing")
    assert harness.githost.pushes == []


def test_a_circular_node_is_refused_as_circular(harness: Harness) -> None:
    """Once the claim has merged, graph.json carries the cause and the frontier leaves the node
    out; a claim attempt says why instead of "ready and not on the frontier"."""
    rows = [
        {**row, "cause": "circular"} if row["node_id"] == HOLE else row
        for row in graph_rows(harness)
    ]
    commit_graph(harness, rows)
    frontier = json.loads(harness.githost.files["frontier.json"])
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != HOLE]
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.pop("frontier.json", None)
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", json={"node_id": HOLE}, headers=harness.auth(token))
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-circular"), body
    assert "circular" in body["message"] and "defects/" in body["message"], body["message"]
    assert harness.store.list_claims() == []


def test_a_path_node_is_told_its_claim_may_sit_under_the_hole_below() -> None:
    """F08-T20 (D-12 v3.22): a node taken off along an established path has no claim of its own;
    the refusal must not send the claimant to an empty ``defects/`` directory."""
    err = claims.circular("mid", {"status": "ready"})
    assert "nodes/mid/defects/" in err.message
    assert "hole below it" in err.message
