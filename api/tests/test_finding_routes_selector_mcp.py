"""F29-T4 (R8, AC10; D-25, D-28 v3.44): the MCP carries labels, approaches and the selector.

``list_sufficient_sets`` carries, per route, its ``approach`` and per hole its ``label``, both
read from ``graph.json`` (F29-R3, R4), and the selector tree over its sets
(``opn_gate.routes.selector_tree``, R6), whose leaves are the published sets. ``get_node``
carries the node's ``label``, ``label_source`` and ``claim`` as ``graph.json`` does; on a
product rendered before v3.44 the label is the id, its source ``id``, the claim null. Both
answers validate against their result schemas, versioned v2.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient, seed_node
from test_target_routes import doc, hole, node

from opn_api.mcp import results
from opn_gate import routes

ROUTES_TARGET = "labelled"
APPROACHES = {"t@1": "split at the median", "t@2": "bound the tail directly"}
LABELS = {"t--h1": "the median bound", "t--h2": "the tail bound", "t--h3": "the small case"}


def labelled_graph() -> dict[str, Any]:
    """Two routes at the root, the first with a hole that has two routes of its own: four sets,
    every route with an approach and every hole with a label, as graph/v12 publishes them."""
    g = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1", decompositions=[["t--h1--h1"], ["t--h3"]], deps=["t--h1--h1", "t--h3"]),
        hole("t--h1--h1"),
        hole("t--h2"),
        hole("t--h3"),
    )
    g["schema"] = "graph/v12"
    g["target_id"] = ROUTES_TARGET
    for row in g["nodes"]:
        row["label"] = LABELS.get(row["node_id"], row["node_id"])
        row["label_source"] = "hole" if row["node_id"] in LABELS else "id"
        row["claim"] = None
        for k, d in enumerate(row.get("decompositions") or [], start=1):
            d["approach"] = APPROACHES.get(f"{row['node_id']}@{k}")
    return g


def seed_routes(harness: Harness, graph: dict[str, Any]) -> None:
    harness.githost.files[f"targets/{ROUTES_TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()


def leaves(t: dict[str, Any]) -> list[str]:
    if t["set"] is not None:
        return [str(t["set"])]
    return [s for c in t["children"] for s in leaves(c)]


# --- the library's fields ---------------------------------------------------------------------


def test_a_route_carries_its_approach_and_a_hole_its_label() -> None:
    found = routes.read(labelled_graph(), ())
    by_id = {r.id: r for r in found.routes}
    assert by_id["t@1"].approach == APPROACHES["t@1"]
    assert by_id["t@2"].approach == APPROACHES["t@2"]
    assert by_id["t--h1@1"].approach is None  # the record names none
    assert [h.label for h in by_id["t@1"].holes] == [LABELS["t--h1"]]
    assert [h.label for h in by_id["t--h1@2"].holes] == [LABELS["t--h3"]]
    d = by_id["t@1"].as_dict()
    assert d["approach"] == APPROACHES["t@1"] and d["holes"][0]["label"] == LABELS["t--h1"]


def test_an_older_product_answers_none_for_both() -> None:
    """A graph rendered before v3.44 has neither field: None, never a crash or an id."""
    found = routes.read(doc(node("t", decompositions=[["t--h1"]], deps=["t--h1"]), hole("t--h1")))
    (route,) = found.routes
    assert route.approach is None and route.holes[0].label is None
    assert route.as_dict()["approach"] is None and route.as_dict()["holes"][0]["label"] is None


# --- list_sufficient_sets ---------------------------------------------------------------------


def test_list_sufficient_sets_carries_the_selector_whose_leaves_are_the_sets(
    harness: Harness,
) -> None:
    graph = labelled_graph()
    seed_routes(harness, graph)
    got = McpClient(harness).ok("list_sufficient_sets", {"target_id": ROUTES_TARGET})
    assert results.violations("list_sufficient_sets", got) == [], results.violations(
        "list_sufficient_sets", got
    )
    assert len(got["sets"]) == 3, [s["routes"] for s in got["sets"]]
    selector = got["selector"]
    assert selector == routes.selector_tree(routes.read(graph, ())).as_dict()
    assert set(selector) == {"route", "node", "set", "sets", "children"}
    assert selector["node"] == "t" and selector["sets"] == 3
    assert leaves(selector) == [s["id"] for s in got["sets"]]
    assert [c["route"] for c in selector["children"]] == ["t@1", "t@2"]
    # the second choice nests under the first branch: coarse to fine
    assert selector["children"][0]["node"] == "t--h1"
    assert [c["route"] for c in selector["children"][0]["children"]] == ["t--h1@1", "t--h1@2"]


def test_list_sufficient_sets_carries_each_routes_approach_and_each_holes_label(
    harness: Harness,
) -> None:
    seed_routes(harness, labelled_graph())
    got = McpClient(harness).ok("list_sufficient_sets", {"target_id": ROUTES_TARGET})
    by_id = {r["id"]: r for r in got["routes"]}
    assert by_id["t@1"]["approach"] == APPROACHES["t@1"]
    assert by_id["t@2"]["approach"] == APPROACHES["t@2"]
    assert by_id["t--h1@1"]["approach"] is None
    assert by_id["t@1"]["holes"][0]["label"] == LABELS["t--h1"]
    assert by_id["t--h1@2"]["holes"][0]["label"] == LABELS["t--h3"]
    assert by_id["t--h1@1"]["holes"][0]["label"] == "t--h1--h1"  # the id, as graph.json has it


def test_the_answer_is_versioned_v2(harness: Harness) -> None:
    """The result schema moved to v2 for the three fields; v1 is still served by name."""
    assert results.schema_id("list_sufficient_sets") == "mcp/list_sufficient_sets/v2"
    client = McpClient(harness)
    assert client.ok("get_schema", {"name": "mcp/list_sufficient_sets/v2"}) == results.load(
        "list_sufficient_sets"
    )
    assert client.ok("get_schema", {"name": "mcp/list_sufficient_sets/v1"}) == results.load(
        "list_sufficient_sets", "v1"
    )
    seed_routes(harness, labelled_graph())
    got = client.ok("list_sufficient_sets", {"target_id": ROUTES_TARGET})
    assert results.violations("list_sufficient_sets", got) == []
    with pytest.raises(KeyError):
        results.load("list_sufficient_sets", "v9")


# --- get_node -----------------------------------------------------------------------------------


def with_labels(harness: Harness, **fields: Any) -> None:
    """The harness's committed ``graph.json`` with ``fields`` on the fixture node's row."""
    raw = harness.githost.files[f"targets/{TARGET}/graph.json"]
    graph = json.loads(raw)
    for row in graph["nodes"]:
        if row["node_id"] == NODE:
            row.update(fields)
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()


def test_get_node_carries_label_source_and_claim_from_graph_json(harness: Harness) -> None:
    seed_node(harness)
    with_labels(harness, label="associativity", label_source="gloss", claim="(a \\land b) \\land c")
    got = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert results.violations("get_node", got) == [], results.violations("get_node", got)
    assert got["label"] == "associativity"
    assert got["label_source"] == "gloss"
    assert got["claim"] == "(a \\land b) \\land c"
    assert results.schema_id("get_node") == "mcp/get_node/v2"


def test_get_node_falls_back_on_an_older_row(harness: Harness) -> None:
    """The harness's fixture graph predates the fields: the label is the id, its source ``id``,
    the claim null."""
    seed_node(harness)
    got = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert results.violations("get_node", got) == []
    assert got["label"] == NODE and got["label_source"] == "id" and got["claim"] is None
