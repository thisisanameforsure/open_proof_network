"""mcpfix WA2 items 3 and 4 (testers 2026-11-25, qa-ea B3): ``list_sufficient_sets`` and
``list_error_codes`` answer compactly by default.

Live, ``list_sufficient_sets {"target_id": "erdos-1094", "cut": "any"}`` answered 1,057,245
characters (569 sets and their selector tree), and ``list_error_codes {}`` 136,281. The owner's
ruling: compact and paged by default. Here the sets come in pages of 20 with an honest ``count``
and ``truncated``, one set by ``set_id``, the selector tree only on ``include_selector``; the
error catalog by default is each code with its meaning, a ``code`` is looked up exactly (a near
miss names the close codes), and ``full: true`` is ``GET /errors.json`` as it was.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api_fakes import Harness
from mcp_client import McpClient
from mcpfix_wa2_fixture import compact

from opn_api.mcp import results
from opn_gate import codes, routes

LIVE = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "routes"
TARGET = "erdos-1094"
BUDGET = 25_000


def seed(harness: Harness) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    graph: dict[str, Any] = json.loads((LIVE / f"{TARGET}.json").read_text("utf-8"))["graph"]
    harness.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    entries: list[dict[str, Any]] = harness.client.get("/frontier.json").json()["entries"]
    return graph, entries


# --- item 3: list_sufficient_sets -------------------------------------------------------------


def test_sets_come_in_pages_of_five_with_an_honest_count(harness: Harness) -> None:
    graph, entries = seed(harness)
    every = routes.read(graph, entries, cut="any").as_dict()["sets"]
    out = McpClient(harness).ok("list_sufficient_sets", {"target_id": TARGET, "cut": "any"})
    assert out["count"] == len(every) == 225
    # mcpfix lead (2026-11-25): pages of 5 (erdos-1094 live: 20 sets were 62,088 characters)
    assert [s["id"] for s in out["sets"]] == [s["id"] for s in every[:5]]
    assert out["truncated"] is True and out["next"] == "5"
    assert "selector" not in out
    assert results.violations("list_sufficient_sets", out) == []
    last = McpClient(harness).ok(
        "list_sufficient_sets", {"target_id": TARGET, "cut": "any", "cursor": "220"}
    )
    assert [s["id"] for s in last["sets"]] == [s["id"] for s in every[220:]]
    assert last["next"] is None


def test_the_routes_answered_are_the_ones_the_page_uses(harness: Harness) -> None:
    graph, entries = seed(harness)
    out = McpClient(harness).ok(
        "list_sufficient_sets", {"target_id": TARGET, "cut": "any", "limit": 2}
    )
    every = routes.read(graph, entries, cut="any").as_dict()

    def used(sets: list[dict[str, Any]]) -> set[str]:
        return {r for s in sets for r in (*s["routes"], *s["proof_routes"])}

    orphans = {r["id"] for r in every["routes"]} - used(every["sets"])  # dead or unresolved
    assert {r["id"] for r in out["routes"]} == used(out["sets"]) | orphans
    assert len(out["routes"]) < len(every["routes"])


def test_one_set_by_id(harness: Harness) -> None:
    graph, entries = seed(harness)
    every = routes.read(graph, entries, cut="any").as_dict()["sets"]
    wanted = every[100]
    client = McpClient(harness)
    out = client.ok(
        "list_sufficient_sets",
        {"target_id": TARGET, "cut": "any", "set_id": wanted["id"], "detail": "full"},
    )
    assert out["sets"] == [wanted] and out["count"] == 1
    missing = client.failed("list_sufficient_sets", {"target_id": TARGET, "set_id": "s-0000000000"})
    assert missing["error"] == "not-found"


def test_the_selector_only_when_asked(harness: Harness) -> None:
    graph, entries = seed(harness)
    out = McpClient(harness).ok(
        "list_sufficient_sets", {"target_id": TARGET, "include_selector": True}
    )
    assert out["selector"] == routes.selector_tree(routes.read(graph, entries)).as_dict()


# --- item 4: list_error_codes -----------------------------------------------------------------


def test_error_codes_by_default_are_each_code_and_its_meaning(harness: Harness) -> None:
    out = McpClient(harness).ok("list_error_codes", {})
    assert len(compact(out)) < BUDGET, len(compact(out))
    assert out["count"] == len(codes.CATALOG)
    first = sorted(codes.CATALOG)[0]
    assert out["codes"][0] == {"code": first, "meaning": codes.CATALOG[first].meaning}


def test_a_code_is_looked_up_exactly(harness: Harness) -> None:
    out = McpClient(harness).ok("list_error_codes", {"code": "witness-sorry"})
    assert out["codes"] == [codes.CATALOG["witness-sorry"].as_dict("witness-sorry")]


def test_an_unknown_code_is_not_found_and_names_the_close_ones(harness: Harness) -> None:
    out = McpClient(harness).failed("list_error_codes", {"code": "witnes-sorry"})
    assert out["error"] == "not-found"
    assert "witness-sorry" in out["message"]


def test_error_codes_full_is_the_plain_path(harness: Harness) -> None:
    client = McpClient(harness)
    assert (
        client.ok("list_error_codes", {"full": True}) == harness.client.get("/errors.json").json()
    )
    assert (
        client.ok("list_error_codes", {"full": True, "prefix": "witness-"})
        == harness.client.get("/errors.json?prefix=witness-").json()
    )


def test_a_prefix_still_narrows_the_default(harness: Harness) -> None:
    out = McpClient(harness).ok("list_error_codes", {"prefix": "witness-"})
    assert out["codes"] and all(set(r) == {"code", "meaning"} for r in out["codes"])
    assert all(r["code"].startswith("witness-") for r in out["codes"])
    assert results.violations("list_error_codes", out) == []
