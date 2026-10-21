"""F27-T2 (D-25, D-28 v3.40): ``list_sufficient_sets``, a target's routes and sufficient sets.

The tool reads ``targets/<id>/graph.json`` at main and the frontier the service serves, and
answers ``opn_gate.routes.read`` over the two — the function the site renders from, so the page
and the tool cannot disagree (F27-Q1). The graph seeded here is erdos-1094 as the graph published
it at commit 6c3a33886 (``gate/tests/fixtures/routes/``).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient

from opn_api.mcp import bijection, results
from opn_gate import closing, routes

LIVE = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "routes"
TARGET = "erdos-1094"


def seed(harness: Harness) -> dict[str, Any]:
    graph: dict[str, Any] = json.loads((LIVE / f"{TARGET}.json").read_text("utf-8"))["graph"]
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    return graph


def served_entries(client: McpClient) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = client.ok("list_frontier", {})["entries"]
    return entries


def test_list_sufficient_sets_round_trip(harness: Harness) -> None:
    """AC9: listed read-only with its bijection row; the answer is the library's over the two
    products, and it validates against its schema."""
    graph = seed(harness)
    client = McpClient(harness)
    (tool,) = [t for t in client.list_tools() if t.name == "list_sufficient_sets"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    row = bijection.BY_TOOL["list_sufficient_sets"]
    assert row.kind == "read"
    assert row.plain == ("targets/<id>/graph.json", "GET /frontier.json")

    got = client.ok("list_sufficient_sets", {"target_id": TARGET})
    assert results.violations("list_sufficient_sets", got) == []
    found = routes.read(graph, served_entries(client))
    expected = found.as_dict()
    assert {
        k: v for k, v in got.items() if k not in {"read_at", "closable", "selector"}
    } == expected
    assert got["closable"] == [c.as_dict() for c in closing.closable(graph)]
    assert got["selector"] == routes.selector_tree(found).as_dict()  # F29-T4
    assert got["cut"] == "finest"
    assert len(got["routes"]) == 16
    assert len(got["sets"]) == 4  # every full expansion (F27-T7)
    assert isinstance(got["read_at"], str)


def test_cut_any_adds_the_coarser_sets_up_to_the_cap(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F27-R8: ``cut: any`` returns every coarser cut; the service's cap truncates and says so."""
    seed(harness)
    client = McpClient(harness)
    coarse = client.ok("list_sufficient_sets", {"target_id": TARGET, "cut": "any"})
    assert (len(coarse["sets"]), coarse["truncated"]) == (225, False)
    monkeypatch.setattr(
        harness.context, "settings", replace(harness.context.settings, routes_max_sets=10)
    )
    capped = client.ok("list_sufficient_sets", {"target_id": TARGET, "cut": "any"})
    assert capped["truncated"] is True
    assert len(capped["sets"]) <= 10
    assert results.violations("list_sufficient_sets", capped) == []


def test_unknown_target_and_bad_cut_are_refused(harness: Harness) -> None:
    seed(harness)
    client = McpClient(harness)
    missing = client.failed("list_sufficient_sets", {"target_id": "no-such-target"})
    assert (missing["error"], missing["source"]) == ("not-found", "graph")
    assert results.violations("list_sufficient_sets", missing) == []
    bad = client.failed("list_sufficient_sets", {"target_id": TARGET, "cut": "widest"})
    assert bad["error"] == "arguments-invalid"
    assert results.violations("list_sufficient_sets", bad) == []
    worse = client.failed("list_sufficient_sets", {"target_id": TARGET, "at_proved": "through"})
    assert worse["error"] == "arguments-invalid"
    assert results.violations("list_sufficient_sets", worse) == []


def test_at_proved_follow_lists_what_each_proved_statement_rests_on(harness: Harness) -> None:
    """F27-T9 (R13, AC13): erdos-1094 as published on 2026-10-19, whose ``h2--h2--h2`` is proved
    by closure. ``at_proved: follow`` answers the library's own follow reading: the same sets
    (ids, open statements, selector) with the proved structure beneath each proved statement
    listed, and ``proof_routes`` naming the assemblies the proofs went through; the default
    stops, as before, and both validate against ``v3``."""
    graph: dict[str, Any] = json.loads((LIVE / f"{TARGET}-20261019.json").read_text("utf-8"))[
        "graph"
    ]
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    client = McpClient(harness)
    stop = client.ok("list_sufficient_sets", {"target_id": TARGET})
    follow = client.ok("list_sufficient_sets", {"target_id": TARGET, "at_proved": "follow"})
    assert results.version_of("list_sufficient_sets") == "v4"  # F09-T76: settles, side
    for got in (stop, follow):
        assert results.violations("list_sufficient_sets", got) == []
    assert (stop["at_proved"], follow["at_proved"]) == ("stop", "follow")
    entries = served_entries(client)
    expected = routes.read(graph, entries, at_proved="follow").as_dict()
    assert {k: v for k, v in follow.items() if k not in {"read_at", "closable", "selector"}} == (
        expected
    )
    assert [s["id"] for s in stop["sets"]] == [s["id"] for s in follow["sets"]]
    assert [s["open"] for s in stop["sets"]] == [s["open"] for s in follow["sets"]]
    assert stop["selector"] == follow["selector"]
    deep = "erdos-1094--h2--h2--h2--h3--h1--h1--h1"
    for a, b in zip(stop["sets"], follow["sets"], strict=True):
        assert a["proof_routes"] == []
        assert "erdos-1094--h2--h2--h2@1" in b["proof_routes"]
        assert deep in b["proved"] and deep not in a["proved"]
        assert b["closed"] > a["closed"] and b["remaining"] == a["remaining"]


def test_a_target_with_no_routes_is_its_own_set(harness: Harness) -> None:
    """A root with no decomposition and one declared dependency: no route, and the one set is
    the root with the dependency a proof of it waits on (D-3)."""
    graph = {
        "schema": "graph/v9",
        "target_id": "plain",
        "root": "plain",
        "nodes": [
            {"node_id": "plain", "status": "blocked", "deps": ["lemma"], "origin": "authored"},
            {"node_id": "lemma", "status": "ready", "deps": [], "origin": "authored"},
        ],
    }
    harness.githost.files["targets/plain/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    got = McpClient(harness).ok("list_sufficient_sets", {"target_id": "plain"})
    assert got["routes"] == []
    assert [s["open"] for s in got["sets"]] == [["lemma", "plain"]]
    assert results.violations("list_sufficient_sets", got) == []


def test_both_sides_reach_the_tool_with_the_fork(harness: Harness) -> None:
    """F09-T76 (D-25, D-28 v3.46): the erdos-257 shape — a root with one route and a refutes
    variant with its own — answers one set per side, each saying which way it settles, the
    selector forking on the side with the proving family first, and validates against v4."""
    graph: dict[str, Any] = json.loads((LIVE / "erdos-257-shape.json").read_text("utf-8"))["graph"]
    harness.githost.files["targets/erdos-257/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    client = McpClient(harness)
    got = client.ok("list_sufficient_sets", {"target_id": "erdos-257"})
    assert results.violations("list_sufficient_sets", got) == [], results.violations(
        "list_sufficient_sets", got
    )
    assert [(s["settles"], s["variant"]) for s in got["sets"]] == [
        ("proves", None),
        ("refutes", "spec-a70fcca4"),
    ]
    expected = routes.read(graph, served_entries(client))
    assert {k: v for k, v in got.items() if k not in {"read_at", "closable", "selector"}} == (
        expected.as_dict()
    )
    selector = got["selector"]
    assert selector == routes.selector_tree(expected).as_dict()
    assert (selector["node"], selector["side"], selector["sets"]) == (None, None, 2)
    assert [(c["side"], c["set"]) for c in selector["children"]] == [
        ("proves", got["sets"][0]["id"]),
        ("refutes", got["sets"][1]["id"]),
    ]
    (tool,) = [t for t in client.list_tools() if t.name == "list_sufficient_sets"]
    assert "refutes" in (tool.description or "")
    # the erdos-1094 shape has one side: no fork, side null everywhere, still v4-valid
    seed(harness)
    one = client.ok("list_sufficient_sets", {"target_id": TARGET})
    assert results.violations("list_sufficient_sets", one) == []
    assert one["selector"]["side"] is None and one["selector"]["node"] is not None
    assert {s["settles"] for s in one["sets"]} == {"proves"}


def test_closable_nodes_ride_with_the_routes(harness: Harness) -> None:
    """F28-T4 (R12): the graph of 2026-10-15 (graph edadad318), whose node the owner asked about
    is closable through its one route; the answer names it, its link and that it is ready, the
    library's own reading, and validates."""
    graph: dict[str, Any] = json.loads((LIVE / f"{TARGET}-20261015.json").read_text("utf-8"))[
        "graph"
    ]
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    got = McpClient(harness).ok("list_sufficient_sets", {"target_id": TARGET})
    assert results.violations("list_sufficient_sets", got) == []
    assert got["closable"] == [
        {
            "node": "erdos-1094--h2--h2--h2--h2",
            "link": {
                "kind": "route",
                "id": "erdos-1094--h2--h2--h2--h2@1",
                "inputs": ["erdos-1094--h2--h2--h2--h2--h1"],
            },
            "ready": True,
        }
    ]
