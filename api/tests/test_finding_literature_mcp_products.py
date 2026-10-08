"""F09-T24: the literature routes reach the MCP, and the products' new versions reach the api
(D-25, D-32 v3.35; the amendment of 2026-10-08 §2).

Two write tools, ``propose_literature`` and ``confirm_literature``, each forwarding to its route
with the caller's bearer (D-28: no MCP-only capability, and no route without its tool), with
result schemas beside the adapter (F09-Q5). The gate now emits ``graph/v6``, ``frontier/v5`` and
``context/v5`` — ``circular``, ``literature``, ``literature_proposed`` on every node — and the
live graph stays on the old versions until its re-pin, so the service serves both: a committed
``frontier/v5`` through ``GET /frontier.json`` and ``list_frontier`` (whose filters are drawn from
the newest version, so the three fields are filterable), a committed ``context/v5`` through
``get_node``. The v5 and v6 documents here are hand-written to the committed schemas and checked
against them, never regenerated fixtures (the gate agent's).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import FIXTURES, TUTORIAL_NODE, Harness, make_harness
from mcp_client import NODE, NODE_DIR, McpClient
from test_literature_route import proposal, seed_stewards
from test_mcp_equivalence import derived_bundle, seed_graph

from opn_api import routes
from opn_api.mcp import bijection, reads, results
from opn_api.mcp.server import TITLES, TOOLS
from opn_gate import schemas, steward

PROPOSE = "propose_literature"
CONFIRM = "confirm_literature"
NEW_FIELDS = ("circular", "literature", "literature_proposed")
LISTED_NODE = "listed-lemma"
BY_NAME = {t.name: t for t in TOOLS}


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    key = tmp_path_factory.mktemp("approval") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "approval"],
        check=True,
    )
    return key.read_text(), key.with_suffix(".pub").read_text().strip()


# --- the tools -----------------------------------------------------------------------------------


def test_the_two_tools_are_bearer_writes_with_rows_titles_and_schemas() -> None:
    """D-28: a tool per route, a row per tool, a result schema per tool, a title per tool."""
    for name, route in ((PROPOSE, "POST /literature"), (CONFIRM, "POST /literature/confirm")):
        tool = BY_NAME[name]
        assert tool.write and tool.access == "bearer", name
        assert bijection.BY_TOOL[name].routes == (route,), name
        assert bijection.BY_TOOL[name].kind == "write"
        assert name in results.known(), name
        assert name in TITLES, name
        assert "literature/v1" in tool.description, name
        assert tool.input_schema["additionalProperties"] is False
    assert set(BY_NAME[PROPOSE].input_schema["required"]) == {
        "node_id",
        "status",
        "references",
        "summary",
    }
    assert set(BY_NAME[CONFIRM].input_schema["required"]) == {
        "node_id",
        "record",
        "status",
        "references",
        "summary",
    }
    labels = {r.label for r in routes.ROUTES}
    assert labels >= routes.LITERATURE_ROUTES
    assert bijection.problems({t.name for t in TOOLS}, labels) == []


def test_propose_literature_forwards_to_its_route(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    args = {k: v for k, v in proposal().items() if k != "model_and_tooling"}
    out = McpClient(harness).ok(PROPOSE, args, token=token)
    assert out["status"] == 201, out
    assert set(out["body"]) == {"id", "path", "pr_url", "pr_number"}
    assert out["body"]["path"].endswith("/literature/20260909T120000Z-alice.yaml")
    [push] = harness.githost.pushes
    doc = yaml.safe_load(next(iter(push.files.values())))
    assert schemas.violations(doc, "literature/v1") == []
    assert doc["contributor"] == "alice" and doc["signature"] is None
    assert results.violations(PROPOSE, out) == []


def test_propose_literature_without_a_bearer_is_refused_before_the_route(
    harness: Harness,
) -> None:
    doc = McpClient(harness).failed(PROPOSE, proposal())
    assert doc["status"] == 401
    assert harness.githost.pushes == []


def confirm_args(**over: Any) -> dict[str, Any]:
    return {
        "node_id": TUTORIAL_NODE,
        "record": None,
        "status": "elementary",
        "references": [{"title": "Hardy and Wright, ch. 22", "url": None, "note": None}],
        "summary": "A textbook fact.",
    } | over


def test_confirm_literature_forwards_with_a_stewards_bearer(approval: tuple[str, str]) -> None:
    """An agent acting for a steward: the bearer's identity is her GitHub login, so the route
    signs as her; the receipt is the route's own."""
    h = make_harness({"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})
    with h.client:
        seed_stewards(h, ("alice", steward.COMMIT))
        token = h.token_for("code_alice", "alice-agent")
        out = McpClient(h).ok(CONFIRM, confirm_args(), token=token)
        assert out["status"] == 201, out
        assert set(out["body"]) == {"pr_number", "pr_url", "branch", "path"}
        assert out["body"]["path"].endswith("/literature/20260909T120000Z-alice.yaml")
        [push] = h.githost.pushes
        doc = yaml.safe_load(next(iter(push.files.values())))
        assert schemas.violations(doc, "literature/v1") == []
        assert (doc["contributor"], doc["via"], doc["confirms"]) == ("alice", "approval-key", None)
        assert doc["key"].split()[:2] == approval[1].split()[:2]
        assert results.violations(CONFIRM, out) == []


def test_confirm_literature_passes_the_routes_refusal_through(
    approval: tuple[str, str],
) -> None:
    h = make_harness({"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})
    with h.client:
        token = h.token_for("code_bob", "bob")  # no steward record, not a curator
        doc = McpClient(h).failed(CONFIRM, confirm_args(), token=token)
        assert doc["status"] == 403 and doc["body"]["error"] == "not-steward-or-curator"
        assert h.githost.pushes == []
        assert results.violations(CONFIRM, doc) == []


# --- the products' new versions ------------------------------------------------------------------


def frontier_v5() -> dict[str, Any]:
    """The v4 golden fixture lifted to v5 by hand: the three new fields on every entry, the
    listed node carrying a proposed status, checked against the committed schema."""
    doc: dict[str, Any] = json.loads((FIXTURES / "frontier-listed.json").read_text())
    assert doc["schema"] == "frontier/v4"
    doc["schema"] = "frontier/v5"
    for entry in doc["entries"]:
        entry["circular"] = []
        entry["literature"] = None
        entry["literature_proposed"] = None
    listed = next(e for e in doc["entries"] if e["node_id"] == LISTED_NODE)
    listed["literature_proposed"] = {
        "status": "known",
        "record": "literature/20261008T090000Z-bob.yaml",
        "contributor": "bob",
    }
    assert schemas.violations(doc, "frontier/v5") == [], "the hand-written v5 is not v5"
    return doc


def serve_frontier(harness: Harness, doc: dict[str, Any]) -> None:
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.githost.files["targets/index.json"] = (
        FIXTURES / "targets-index-listed.json"
    ).read_bytes()
    harness.context.files.clear()


def test_a_v5_frontier_is_served(harness: Harness) -> None:
    serve_frontier(harness, frontier_v5())
    r = harness.client.get("/frontier.json")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["schema"] == "frontier/v5"
    assert schemas.violations(doc) == []
    entry = next(e for e in doc["entries"] if e["node_id"] == LISTED_NODE)
    assert entry["literature_proposed"]["status"] == "known"
    assert entry["circular"] == [] and entry["literature"] is None


def test_a_v4_frontier_is_still_served(harness: Harness) -> None:
    doc = json.loads((FIXTURES / "frontier-listed.json").read_text())
    serve_frontier(harness, doc)
    r = harness.client.get("/frontier.json")
    assert r.status_code == 200 and r.json()["schema"] == "frontier/v4"


def test_list_frontier_filters_on_the_new_fields(harness: Harness) -> None:
    """The filter set is drawn from the newest version, so an agent can ask for the nodes whose
    proposed status awaits a steward, or those under no circularity claim."""
    for field in NEW_FIELDS:
        assert field in reads._entry_fields(), field
        assert f"`{field}`" in reads.filters_param()["description"], field
    serve_frontier(harness, frontier_v5())
    client = McpClient(harness)
    got = client.ok("list_frontier", {"filters": {"literature_proposed.status": "known"}})
    assert [e["node_id"] for e in got["entries"]] == [LISTED_NODE]
    assert results.violations("list_frontier", got) == []
    nothing = client.ok("list_frontier", {"filters": {"literature.status": "known"}})
    assert nothing["entries"] == []


def test_get_node_serves_a_committed_v5_context(harness: Harness, tmp_path: Path) -> None:
    """A graph re-rendered under the new pin commits context/v5; the service serves it as the
    file it is, and the tool's result schema admits it."""
    seed_graph(harness)
    derived = derived_bundle(harness, tmp_path / "tree")
    v5 = {
        **derived,
        "schema": "context/v5",
        "circular": [],
        "literature": {
            "status": "known",
            "record": "literature/20261008T090000Z-bob.yaml",
            "contributor": "bob",
            "confirmed_by": "alice",
            "confirmation": "literature/20261008T100000Z-alice.yaml",
        },
        "literature_proposed": None,
    }
    assert schemas.violations(v5, "context/v5") == [], "the hand-written v5 is not v5"
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = schemas.canonical_json(v5)
    harness.context.files.clear()
    served = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert served["context_source"] == "file"
    assert served["context"]["schema"] == "context/v5"
    assert served["context"]["literature"]["confirmed_by"] == "alice"
    assert results.violations("get_node", served) == []


def test_the_index_lists_both_routes_as_bearer_writes(harness: Harness) -> None:
    listed = {(r["method"], r["path"]): r for r in harness.client.get("/").json()["routes"]}
    for label in routes.LITERATURE_ROUTES:
        method, path = label.split(" ", 1)
        assert listed[(method, path)]["auth"] == "bearer", label
        assert "literature" in listed[(method, path)]["purpose"]
