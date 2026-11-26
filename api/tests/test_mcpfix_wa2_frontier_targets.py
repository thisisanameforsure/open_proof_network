"""mcpfix WA2 items 1, 2 and 8 (testers 2026-11-25, qa-ea B3 and B5): ``list_frontier`` and
``list_targets`` answer compactly and in pages by default, and every read that takes a
``target_id`` names an unknown target ``not-found``.

Live, ``read list_targets {}`` answered 1,316,781 characters with no way to narrow it and
``read list_frontier {}`` 355,075 (602 entries). The owner's ruling: a read answers compactly and
in pages by default, starting from the open problems with their basic facts, and the agent then
asks for one problem's open nodes; ``full: true`` answers today's document exactly, so the plain
path's equality (D-28) holds for the full form.
"""

from __future__ import annotations

from typing import Any

from api_fakes import Harness
from mcp_client import McpClient
from mcpfix_wa2_fixture import compact, seed_large, target_id

from opn_api.mcp import results

BUDGET = 25_000


# --- item 1: list_frontier -------------------------------------------------------------------


def test_list_frontier_by_default_is_one_row_per_target_with_open_work(harness: Harness) -> None:
    index, frontier = seed_large(harness)
    out = McpClient(harness).ok("list_frontier", {})
    assert len(compact(out)) < BUDGET, len(compact(out))
    with_work = [t["target_id"] for t in index["targets"] if t["claimable"]]
    assert out["count"] == len(with_work)
    assert out["limit"] == 50 and len(out["targets"]) == 50
    first = out["targets"][0]
    assert first == {
        "target_id": target_id(0),
        "root": target_id(0),
        "track": index["targets"][0]["track"],
        "status": index["targets"][0]["status"],
        "open": 69,
        "claimable": sum(
            1 for e in frontier["entries"] if e["target_id"] == target_id(0) and e["claimable"]
        ),
    }
    assert out["next"] is not None


def test_list_frontier_pages_through_every_target_once(harness: Harness) -> None:
    seed_large(harness)
    client = McpClient(harness)
    seen: list[str] = []
    cursor = None
    while True:
        args: dict[str, Any] = {"limit": 200}
        if cursor is not None:
            args["cursor"] = cursor
        out = client.ok("list_frontier", args)
        seen += [t["target_id"] for t in out["targets"]]
        cursor = out["next"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == out["count"]


def test_list_frontier_with_a_target_answers_its_entries_in_pages(harness: Harness) -> None:
    _, frontier = seed_large(harness)
    client = McpClient(harness)
    mine = [e for e in frontier["entries"] if e["target_id"] == target_id(0)]
    out = client.ok("list_frontier", {"target_id": target_id(0)})
    assert out["target_id"] == target_id(0) and out["count"] == len(mine) == 69
    # mcpfix lead (verifier VA, N2): a target's entries come 20 to a page (50 of erdos-1094's
    # were 32,225 characters live); the open-problems summary keeps 50 rows
    assert [e["node_id"] for e in out["entries"]] == [e["node_id"] for e in mine[:20]]
    seen = [e["node_id"] for e in out["entries"]]
    while out["next"] is not None:
        out = client.ok("list_frontier", {"target_id": target_id(0), "cursor": out["next"]})
        seen += [e["node_id"] for e in out["entries"]]
    assert seen == [e["node_id"] for e in mine]


def test_list_frontier_filters_still_apply_to_entries(harness: Harness) -> None:
    seed_large(harness)
    out = McpClient(harness).ok(
        "list_frontier", {"target_id": target_id(0), "filters": {"claimable": False}}
    )
    assert out["entries"] and all(e["claimable"] is False for e in out["entries"])


def test_list_frontier_full_is_the_plain_path(harness: Harness) -> None:
    seed_large(harness)
    assert (
        McpClient(harness).ok("list_frontier", {"full": True})
        == harness.client.get("/frontier.json").json()
    )


def test_list_frontier_names_an_unknown_target_not_found(harness: Harness) -> None:
    seed_large(harness)
    assert McpClient(harness).failed("list_frontier", {"target_id": "no-such"})["error"] == (
        "not-found"
    )


def test_list_frontier_declares_v2_and_its_answers_validate(harness: Harness) -> None:
    seed_large(harness)
    assert results.version_of("list_frontier") == "v2"
    client = McpClient(harness)
    for args in ({}, {"target_id": target_id(1)}, {"full": True}):
        assert not results.violations("list_frontier", client.ok("list_frontier", args))
    # the first version stays served by name (get_schema)
    assert results.load("list_frontier", "v1")["title"] == "mcp/list_frontier/v1"


# --- item 2: list_targets --------------------------------------------------------------------


def test_list_targets_by_default_is_summary_rows_in_pages(harness: Harness) -> None:
    index, _ = seed_large(harness)
    out = McpClient(harness).ok("list_targets", {})
    assert len(compact(out)) < BUDGET, len(compact(out))
    assert out["count"] == len(index["targets"]) and out["limit"] == 50
    row = index["targets"][0]
    assert out["targets"][0] == {
        k: row[k] for k in ("target_id", "root", "status", "track", "claimable", "node_counts")
    }


def test_list_targets_one_target_answers_all_its_fields(harness: Harness) -> None:
    index, _ = seed_large(harness)
    out = McpClient(harness).ok("list_targets", {"target_id": target_id(7)})
    assert out["targets"] == [index["targets"][7]] and out["count"] == 1


def test_list_targets_fields_project(harness: Harness) -> None:
    seed_large(harness)
    out = McpClient(harness).ok("list_targets", {"fields": ["fidelity"], "limit": 3})
    assert [set(r) for r in out["targets"]] == [{"target_id", "fidelity"}] * 3
    refused = McpClient(harness).failed("list_targets", {"fields": ["nonsense"]})
    assert refused["error"] == "filter-unknown"


def test_list_targets_full_is_the_committed_index(harness: Harness) -> None:
    index, _ = seed_large(harness)
    assert McpClient(harness).ok("list_targets", {"full": True}) == index


def test_list_targets_names_an_unknown_target_not_found(harness: Harness) -> None:
    seed_large(harness)
    assert McpClient(harness).failed("list_targets", {"target_id": "no-such"})["error"] == (
        "not-found"
    )


# --- item 8: one code for an unknown target ---------------------------------------------------

#: Every read that takes a target_id, with the other arguments it needs.
TARGET_READS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("get_target", {}),
    ("get_defs", {}),
    ("get_gate_spec", {}),
    ("get_review", {}),
    ("list_frontier", {}),
    ("list_targets", {}),
    ("list_submissions", {}),
    ("list_words_needed", {}),
    ("list_registrations", {}),
    ("list_review_questions", {}),
    ("list_open_pairs", {}),
    ("list_sufficient_sets", {}),
)


def test_every_read_names_an_unknown_target_not_found(harness: Harness) -> None:
    client = McpClient(harness)
    codes = {
        name: client.failed(name, {"target_id": "no-such-target", **extra})["error"]
        if client.call(name, {"target_id": "no-such-target", **extra}).isError
        else "answered"
        for name, extra in TARGET_READS
    }
    assert codes == dict.fromkeys(codes, "not-found"), codes
