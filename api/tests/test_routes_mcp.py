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
from opn_gate import routes

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
    expected = routes.read(graph, served_entries(client)).as_dict()
    assert {k: v for k, v in got.items() if k != "read_at"} == expected
    assert got["cut"] == "finest"
    assert len(got["routes"]) == 16
    assert len(got["sets"]) == 2
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
