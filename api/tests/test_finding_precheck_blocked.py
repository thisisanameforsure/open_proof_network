"""Finding precheck-blocked (2026-09-13, the Euclid tester): precheck accepts a blocked node.

The tester prechecked the Euclid root while its four holes were unproved. ``POST /precheck``
answered 202, pushed a branch, dispatched a hosted run, and the run failed at the dependency
check minutes later — twice. The service already had every fact it needed to say no: the node's
row in the committed ``graph.json`` says ``blocked``, and which dependencies are unproved.

Mike's decision (2026-09-14, plan F06-T6): after ``node_facts`` and before any job exists,
``POST /precheck`` refuses a blocked node with the same ``409 node-blocked`` the claim route
gives (F05-T9) — naming the unproved dependencies, or ``/proposals/witness`` for a hole blocked
``witness-missing`` — and dispatches nothing. A proved node stays precheckable (D-19 depends on
the tutorial node), and ``get_node`` still serves a blocked node: both pinned here unmarked. The
MCP ``precheck_submission`` passes the refusal through (F09-R7). The three findings were held as
strict xfails from f80151b until F06-T6 landed (conventions §2); the marks came off with the fix.
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import TUTORIAL_PROOF, Harness
from mcp_client import NODE, STATEMENT, TARGET, McpClient, seed_node
from test_finding_mcp_bootstrap import HOLE, add_hole

GRAPH_PATH = f"targets/{TARGET}/graph.json"
PREFIX = f"targets/{TARGET}/nodes/"
UNPROVED_DEP = "tutorial-and-swap"  # ready in the fixture graph
PROVED = "already-proved"  # proved, and the fixture's proved tutorial node


def bundle(node_id: str) -> dict[str, str]:
    return {f"{PREFIX}{node_id}/Proof.lean": TUTORIAL_PROOF}


def block_node(harness: Harness) -> None:
    """``and-reassoc`` blocked on an unproved dependency, and so off the committed frontier."""
    files = harness.githost.files
    graph: dict[str, Any] = json.loads(files[GRAPH_PATH])
    for node in graph["nodes"]:
        if node["node_id"] == NODE:
            node.update(status="blocked", cause=None, deps=[UNPROVED_DEP])
    frontier: dict[str, Any] = json.loads(files["frontier.json"])
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != NODE]
    files[GRAPH_PATH] = json.dumps(graph).encode()
    files["frontier.json"] = json.dumps(frontier).encode()
    # The dependency is a node of the tree, as any dep ``graph.json`` names is: since F08-T10
    # the node bundle reads a node's deps from the graph product (through any revision), so a
    # dep that exists only in a hand-edited graph.json would be unreadable, which no real graph
    # can be.
    files.setdefault(
        f"{PREFIX}{UNPROVED_DEP}/Statement.lean",
        b"theorem OpnProp.and_swap : \xe2\x88\x80 p q : Prop, p \xe2\x88\xa7 q \xe2\x86\x92 "
        b"q \xe2\x88\xa7 p := by\n  sorry\n",
    )
    harness.context.files.clear()


def nothing_started(harness: Harness) -> None:
    assert harness.githost.dispatches == [], "a hosted run was dispatched for a blocked node"
    assert harness.githost.pushes == []
    assert harness.store.jobs == {}


def test_a_dep_blocked_node_is_refused_before_any_job(harness: Harness) -> None:
    block_node(harness)
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle(NODE)}, headers=harness.auth(token)
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    assert UNPROVED_DEP in body["message"], body["message"]
    nothing_started(harness)


def test_a_witness_missing_hole_is_refused_naming_the_witness_route(harness: Harness) -> None:
    add_hole(harness)
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/precheck", json={"node_id": HOLE, "bundle": bundle(HOLE)}, headers=harness.auth(token)
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    assert "/proposals/witness" in body["message"], body["message"]
    nothing_started(harness)


def test_precheck_submission_over_mcp_passes_the_refusal_through(harness: Harness) -> None:
    block_node(harness)
    token = harness.token_for("code_alice", "alice-p")
    doc = McpClient(harness).failed(
        "precheck_submission", {"node_id": NODE, "bundle": bundle(NODE)}, token=token
    )
    assert doc["status"] == 409, doc
    assert doc["body"]["error"] == "node-blocked", doc["body"]
    assert UNPROVED_DEP in doc["body"]["message"]
    nothing_started(harness)


# --- pins: what the fix must not take away --------------------------------------------------------


def test_pin_a_proved_node_stays_precheckable(harness: Harness) -> None:
    """**PIN (D-19).** The tutorial node is normally proved and off the frontier, and its
    anonymous precheck is how every identity is minted; the refusal is for ``blocked`` only.
    Same property as ``test_precheck.py::test_proved_tutorial_node_is_still_precheckable``."""
    r = harness.client.post("/precheck", json={"node_id": PROVED, "bundle": bundle(PROVED)})
    assert r.status_code == 202, r.text
    assert len(harness.githost.dispatches) == 1


def test_pin_a_ready_node_stays_precheckable(harness: Harness) -> None:
    """**PIN.** The refusal does not reach a node that can pass."""
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle(NODE)}, headers=harness.auth(token)
    )
    assert r.status_code == 202, r.text


def test_pin_get_node_still_serves_a_blocked_node(harness: Harness) -> None:
    """**PIN.** Reading a blocked node is how a prover learns what it is waiting on; the
    precheck refusal must not become a read refusal."""
    seed_node(harness)
    block_node(harness)
    node = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert node["node_id"] == NODE and node["target_id"] == TARGET
    assert node["files"]["Statement.lean"] == STATEMENT
    assert node["claims"] is None  # off the frontier, so no overlay entry
