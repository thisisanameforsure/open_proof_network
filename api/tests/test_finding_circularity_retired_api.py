"""F08-T42 (decisions v3.43; D-12, D-16, D-25): the service retires the circularity claim.

A ``circular-decomposition`` claim's exhibit proved that a proof of the hole is a proof of an
ancestor, and the owner's ruling (2026-10-15) is that every hole meets that by its merged
assembly, so the claim and its label separated nothing. The gate's refusal of a hole
*definitionally equal* to an ancestor (``offload-restates-ancestor``) is the whole rule now. The
service's half:

* ``POST /defect-claims`` refuses the class, and an ``ancestor`` on any class, with
  ``defect-class-retired`` (the gate's code for the same record, ``source: both``), and opens
  nothing; every other class is filed as before, at ``defect-claim/v1``;
* ``file_defect_claim`` no longer advertises the class or the ``ancestor`` parameter, and the
  class reaches the route's refusal;
* ``GET /frontier.json`` and ``list_frontier`` serve the gate's ``frontier/v6`` (no
  ``circular``) and still the older versions; ``list_frontier`` has no ``circular`` filter;
* claiming a node never answers ``node-circular``: an old product's ``cause: circular`` is no
  reason the service gives any more.

Red run: ``engineering/evidence/F08/task-42-api-red.txt``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from api_fakes import Harness
from mcp_client import McpClient
from test_claims_defect import FIXTURE_GRAPH, commit_statement, only_file, post

from opn_api.mcp.server import BY_NAME
from opn_gate import schemas

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TARGET = "propositional"
HOLE = "and-reassoc"
ANCESTOR = "and-swap-reassoc"
STATEMENT_PATH = f"targets/{TARGET}/nodes/{HOLE}/Statement.lean"
EXHIBIT = (
    "theorem circular :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) :=\n"
    "  fun _ _ _ _ h => ⟨h.1.1, h.1.2, h.2⟩\n"
)
RETIRED: dict[str, Any] = {
    "stmt_ref": HOLE,
    "class": "circular-decomposition",
    "line": 1,
    "exhibit": EXHIBIT,
}
ORDINARY: dict[str, Any] = {**RETIRED, "class": "junk-value"}
GRAPH_PATH = f"targets/{TARGET}/graph.json"


def commit_hole(h: Harness) -> None:
    """The hole's committed Statement.lean, which the line check reads."""
    h.githost.files[STATEMENT_PATH] = (FIXTURE_GRAPH / TARGET / STATEMENT_PATH).read_bytes()


def refused_retired(r: Any) -> None:
    body = r.json()
    assert (r.status_code, body.get("error")) == (400, "defect-class-retired"), body
    assert "v3.43" in body["message"] or "retired" in body["message"], body["message"]


# --- POST /defect-claims -------------------------------------------------------------------------


def test_the_retired_class_is_refused_and_opens_nothing(harness: Harness) -> None:
    commit_hole(harness)
    token = harness.token_for("code_alice", "alice")
    refused_retired(post(harness, "/defect-claims", token, RETIRED))
    refused_retired(post(harness, "/defect-claims", token, {**RETIRED, "ancestor": ANCESTOR}))
    assert harness.githost.pushes == [], "a refused claim opens nothing"


def test_an_ancestor_on_any_other_class_is_refused_as_retired(harness: Harness) -> None:
    commit_hole(harness)
    token = harness.token_for("code_alice", "alice")
    refused_retired(post(harness, "/defect-claims", token, {**ORDINARY, "ancestor": ANCESTOR}))
    assert harness.githost.pushes == []


def test_an_ordinary_defect_claim_is_still_filed_at_v1(harness: Harness) -> None:
    commit_hole(harness)
    commit_statement(harness)
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/defect-claims", token, ORDINARY)
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path.startswith(f"targets/{TARGET}/nodes/{HOLE}/defects/")
    doc = yaml.safe_load(content)
    assert (doc["schema"], doc["class"]) == ("defect-claim/v1", "junk-value")
    assert "ancestor" not in doc
    assert schemas.violations(doc, "defect-claim/v1") == []


def test_a_node_with_an_old_circular_cause_takes_ordinary_claims(harness: Harness) -> None:
    """A product rendered before the re-pin may still say ``cause: circular``; nothing reads it."""
    commit_hole(harness)
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [{**r, "cause": "circular"} if r["node_id"] == HOLE else r for r in doc["nodes"]]
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)
    token = harness.token_for("code_alice", "alice")
    refused_retired(post(harness, "/defect-claims", token, RETIRED))
    assert post(harness, "/defect-claims", token, ORDINARY).status_code == 201


# --- the MCP write tool --------------------------------------------------------------------------


def test_file_defect_claim_no_longer_offers_the_class_or_the_ancestor() -> None:
    tool = BY_NAME["file_defect_claim"]
    assert "ancestor" not in tool.input_schema["properties"], tool.input_schema
    assert "circular-decomposition" not in tool.description, tool.description
    assert "circular-decomposition" not in json.dumps(tool.input_schema)
    assert "circular" not in BY_NAME["get_schema"].description


def test_file_defect_claim_refuses_the_class_as_the_route_does(harness: Harness) -> None:
    commit_hole(harness)
    token = harness.token_for("code_alice", "alice")
    got = McpClient(harness).call("file_defect_claim", RETIRED, token=token).structuredContent
    assert got is not None and got["status"] == 400, got
    assert got["body"]["error"] == "defect-class-retired", got
    assert harness.githost.pushes == []


# --- the frontier --------------------------------------------------------------------------------


def frontier_at(version: str) -> dict[str, Any]:
    """The golden frontier, written at ``version``: v6 has no ``circular``, v5 carries one."""
    doc: dict[str, Any] = json.loads((FIXTURES / "frontier-listed.json").read_bytes())
    doc["schema"] = version
    for entry in doc["entries"]:
        entry.pop("circular", None)
        if version == "frontier/v5":
            entry["circular"] = []
    assert schemas.violations(doc, version) == [], f"the hand-written {version} is not {version}"
    return doc


def serve(harness: Harness, doc: dict[str, Any]) -> None:
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.githost.files["targets/index.json"] = (
        FIXTURES / "targets-index-listed.json"
    ).read_bytes()
    harness.context.files.clear()


def test_the_golden_frontier_is_v6() -> None:
    doc = json.loads((FIXTURES / "frontier-listed.json").read_bytes())
    assert doc["schema"] == "frontier/v8"
    assert all("circular" not in e for e in doc["entries"])


def test_frontier_v6_is_served_and_v5_still_is(harness: Harness) -> None:
    for version in ("frontier/v6", "frontier/v5"):
        serve(harness, frontier_at(version))
        r = harness.client.get("/frontier.json")
        assert r.status_code == 200, (version, r.text)
        assert r.json()["schema"] == version
        got = McpClient(harness).ok("list_frontier", {})
        assert got["entries"], version


def test_list_frontier_has_no_circular_filter(harness: Harness) -> None:
    serve(harness, frontier_at("frontier/v6"))
    client = McpClient(harness)
    refused = client.call("list_frontier", {"filters": {"circular": []}}).structuredContent
    assert refused is not None and refused.get("error") == "filter-unknown", refused
    assert "`circular`" not in json.dumps(BY_NAME["list_frontier"].input_schema)


# --- claims --------------------------------------------------------------------------------------


def test_claiming_never_answers_node_circular(harness: Harness) -> None:
    """An off-frontier node whose old row still says ``cause: circular`` is answered as any other
    node that is not on the frontier."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [{**r, "cause": "circular"} if r["node_id"] == HOLE else r for r in doc["nodes"]]
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    frontier = json.loads(harness.githost.files["frontier.json"])
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != HOLE]
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.clear()
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", json={"node_id": HOLE}, headers=harness.auth(token))
    body = r.json()
    assert r.status_code == 409, body
    assert body.get("error") != "node-circular", body
    assert "circular" not in body["message"], body["message"]
    assert harness.store.list_claims() == []
