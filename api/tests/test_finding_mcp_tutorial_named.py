"""F09: the MCP names the tutorial node it tells a client to start on.

The story. Tester agents, 2026-09-27: the server's instructions and the unauthenticated write's
refusal both said "run precheck_submission on the tutorial node" and never said which node that
was. ``list_frontier`` leaves it out, because it is normally proved, so an MCP-only client had
no read that would name it short of calling ``get_target`` on every target.

The rule. The handshake's instructions and the ``unauthenticated`` refusal name the tutorial
node as ``<target>/<node>``, derived at the time of asking from the committed graphs (the rows
with ``tutorial: true``), never from a constant: move the flag and the name moves with it. When
the graph cannot be read, the handshake still answers, in the generic words.
"""

from __future__ import annotations

import json

from api_fakes import Harness
from mcp_client import NODE, McpClient

GRAPH = "targets/propositional/graph.json"


def move_tutorial(h: Harness, to: str) -> None:
    doc = json.loads(h.githost.files[GRAPH])
    for node in doc["nodes"]:
        node["tutorial"] = node["node_id"] == to
    h.githost.files[GRAPH] = json.dumps(doc).encode()
    h.context.files.clear()


def test_the_handshake_names_the_tutorial_node(harness: Harness) -> None:
    move_tutorial(harness, "tutorial-and-swap")
    init = McpClient(harness).initialize()
    assert init.instructions is not None
    assert "propositional/tutorial-and-swap" in init.instructions


def test_the_name_is_derived_not_a_constant(harness: Harness) -> None:
    move_tutorial(harness, "listed-only")
    init = McpClient(harness).initialize()
    assert init.instructions is not None
    assert "propositional/listed-only" in init.instructions
    assert "tutorial-and-swap" not in init.instructions


def test_the_unauthenticated_refusal_names_it(harness: Harness) -> None:
    move_tutorial(harness, "tutorial-and-swap")
    doc = McpClient(harness).failed("claim_node", {"node_id": NODE})
    assert "propositional/tutorial-and-swap" in json.dumps(doc)
    mine = McpClient(harness).failed("list_my_claims", {})
    assert "propositional/tutorial-and-swap" in mine["message"]


def test_the_handshake_survives_an_unreadable_graph(harness: Harness) -> None:
    harness.githost.unreachable = True
    harness.context.files.clear()
    init = McpClient(harness).initialize()
    assert init.instructions is not None
    assert "tutorial node" in init.instructions
