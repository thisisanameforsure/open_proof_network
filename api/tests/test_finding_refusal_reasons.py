"""Finding refusal-reasons (2026-09-13, the Euclid tester): a claim refusal gives no reason.

The tester claimed a hole a merged skeleton had spawned and was told ``404 node-not-in-frontier``
— true, and useless: the hole was ``blocked`` with cause ``witness-missing``, and the way out
(``POST /proposals/witness``) was named nowhere. The same answer comes back for a node blocked
on an unproved dependency, for a proved node, and for a node that does not exist at all; and a
listed target's node answers ``node-not-claimable`` without the reasons ``targets/index.json``
already carries.

Mike's decision (2026-09-14, plan F05-T9): ``POST /claims`` distinguishes the four cases —
unknown -> ``404 node-unknown``; blocked -> ``409 node-blocked`` naming the cause or the unproved
dependencies (a witness-missing hole names ``/proposals/witness``) with ``details == {status,
cause, unproved_deps}``; any other node off the frontier -> ``409 node-not-open`` naming its
status; ``claimable: false`` -> ``409 node-not-claimable`` whose message carries
``intake.explain(r)`` for every reason and whose ``details.not_claimable`` is the list. The MCP
``claim_node`` passes the same body through (F09-R7). Each test was held as a strict xfail from
f80151b until F05-T9 landed (conventions §2); the marks came off with the fix.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api_fakes import Harness
from mcp_client import TARGET, McpClient
from test_claims import FROZEN_NODE, serve_frozen
from test_finding_mcp_bootstrap import HOLE, add_hole

from opn_gate import intake

GRAPH_PATH = f"targets/{TARGET}/graph.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
#: A node blocked on one unproved dependency (``and-reassoc`` is ``ready``) and one proved one
#: (``already-proved``), so the message can be checked for naming only the unproved.
DEP_BLOCKED = "swap-corollary"
PROVED = "already-proved"


def add_dep_blocked(harness: Harness) -> None:
    """A node blocked on an unproved dependency in the committed graph.json (D-25)."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"].append(
        {
            "node_id": DEP_BLOCKED,
            "status": "blocked",
            "cause": None,
            "deps": [PROVED, "and-reassoc"],
            "origin": "authored",
            "statement_hash": "2" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)


def frontier_ids(harness: Harness) -> set[str]:
    served = harness.client.get("/frontier.json")
    assert served.status_code == 200, served.text
    return {str(e["node_id"]) for e in served.json()["entries"]}


def claim(harness: Harness, node_id: str) -> tuple[int, dict[str, Any]]:
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", json={"node_id": node_id}, headers=harness.auth(token))
    body: dict[str, Any] = r.json()
    return r.status_code, body


def test_a_witness_missing_hole_is_refused_with_its_cause_and_the_way_out(
    harness: Harness,
) -> None:
    add_hole(harness)
    assert HOLE not in frontier_ids(harness), "guard: the hole is off the frontier"

    status, body = claim(harness, HOLE)
    assert (status, body.get("error")) == (409, "node-blocked"), body
    assert "witness-missing" in body["message"], body["message"]
    assert "/proposals/witness" in body["message"], body["message"]
    assert body["details"] == {"status": "blocked", "cause": "witness-missing", "unproved_deps": []}
    assert harness.store.list_claims() == []


def test_a_dep_blocked_node_is_refused_naming_the_unproved_dependency(harness: Harness) -> None:
    add_dep_blocked(harness)
    assert DEP_BLOCKED not in frontier_ids(harness), "guard: the node is off the frontier"

    status, body = claim(harness, DEP_BLOCKED)
    assert (status, body.get("error")) == (409, "node-blocked"), body
    assert "and-reassoc" in body["message"], body["message"]
    assert PROVED not in body["message"], "a proved dependency is not what blocks it"
    assert body["details"] == {"status": "blocked", "cause": None, "unproved_deps": ["and-reassoc"]}


def test_a_proved_node_is_refused_as_not_open_naming_its_status(harness: Harness) -> None:
    assert PROVED not in frontier_ids(harness), "guard: the proved node is off the frontier"

    status, body = claim(harness, PROVED)
    assert (status, body.get("error")) == (409, "node-not-open"), body
    # The id itself contains "proved"; the status must be named apart from it.
    assert "proved" in body["message"].replace(PROVED, ""), body["message"]


def test_an_unknown_node_is_refused_as_unknown(harness: Harness) -> None:
    status, body = claim(harness, "no-such-node")
    assert (status, body.get("error")) == (404, "node-unknown"), body


def test_a_frozen_node_is_refused_with_every_not_claimable_reason(harness: Harness) -> None:
    """F14-R1 left a curated target one reason besides a closed status: the drift freeze. The
    refusal still names every reason the index carries, in ``intake.explain``'s words."""
    serve_frozen(harness)
    index = json.loads((FIXTURES / "targets-index-frozen.json").read_bytes())
    row = next(t for t in index["targets"] if t["target_id"] == "frozen-target")
    reasons = [str(r) for r in row["not_claimable"]]
    assert reasons, "guard: the fixture row names reasons"

    status, body = claim(harness, FROZEN_NODE)
    assert (status, body.get("error")) == (409, "node-not-claimable"), body
    for reason in reasons:
        assert intake.explain(reason) in body["message"], (reason, body["message"])
    assert body["details"]["not_claimable"] == reasons


def test_claim_node_over_mcp_carries_the_same_refusal(harness: Harness) -> None:
    add_hole(harness)
    token = harness.token_for("code_alice", "alice-p")
    over_http = harness.client.post("/claims", json={"node_id": HOLE}, headers=harness.auth(token))
    over_mcp = McpClient(harness).failed("claim_node", {"node_id": HOLE}, token=token)
    assert over_mcp["status"] == over_http.status_code
    assert over_mcp["body"] == over_http.json()
    assert over_mcp["body"]["error"] == "node-blocked", over_mcp["body"]
    assert "/proposals/witness" in over_mcp["body"]["message"]
