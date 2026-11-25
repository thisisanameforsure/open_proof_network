"""mcpfix (lead, 2026-11-25): list_sufficient_sets' route rows are compact by default.

WA2 paged the sets, but on the live erdos-1094 the default answer was still 98,730 characters,
52,872 of them route rows: each hole repeats its label, attempts, refuted classes and ready-since,
and each route its approach text. By default a route row now says what a reader needs to choose a
set (id, node, live, resolved, each hole's node and status, the summary's counts);
``detail: "full"`` answers the rows as they were."""

from __future__ import annotations

from typing import Any

from api_fakes import Harness
from mcp_client import McpClient
from test_mcpfix_wa2_sets_codes import TARGET, seed

from opn_api.mcp import results
from opn_gate import routes

COMPACT_KEYS = {"id", "node", "live", "resolved", "holes", "summary"}
COMPACT_HOLE = {"node", "status"}
COMPACT_SUMMARY = {"holes", "proved", "open", "dead", "unresolved"}


def test_route_rows_are_compact_by_default(harness: Harness) -> None:
    seed(harness)
    out = McpClient(harness).ok("list_sufficient_sets", {"target_id": TARGET, "cut": "any"})
    assert out["routes"]
    for r in out["routes"]:
        assert set(r) == COMPACT_KEYS, r.keys()
        assert all(set(h) == COMPACT_HOLE for h in r["holes"])
        assert set(r["summary"]) == COMPACT_SUMMARY
    assert out["detail"] == "compact"
    assert all("statements" not in s for s in out["sets"])
    assert results.violations("list_sufficient_sets", out) == []


def test_full_detail_is_the_rows_as_they_were(harness: Harness) -> None:
    graph, entries = seed(harness)
    every: dict[str, Any] = {
        r["id"]: r for r in routes.read(graph, entries, cut="any").as_dict()["routes"]
    }
    out = McpClient(harness).ok(
        "list_sufficient_sets", {"target_id": TARGET, "cut": "any", "detail": "full"}
    )
    assert out["detail"] == "full"
    for r in out["routes"]:
        assert r == every[r["id"]]
