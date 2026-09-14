"""Finding frontier-lag (2026-09-13, the Euclid tester): the frontier lags ``info.json`` by the
cache window.

Every committed file the service reads has its own cache entry, revalidated on its own clock
(F05-R9). After a merge the tester read ``server_info`` and saw the new ``rendered_from`` while
``list_frontier`` still served the frontier of the commit before — one service, two graph
commits, for up to a whole window. Nothing ties the entries together.

Mike's decision (2026-09-14, plan F05-T10): one freshness generation. ``info.json``'s ETag is the
marker: when its revalidation finds a new one, every other cached file is stale at once, in both
``committed()`` copies (``frontier.py`` and ``mcp/reads.py``). The tests move ``main`` from
``5*40`` to ``6*40`` in the fake host and age ``info.json`` alone; the frontier and the target
graph must follow. Strict xfails until F05-T10 lands (conventions §2).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import TARGET, McpClient
from test_frontier import force_stale

OLD = "5" * 40
NEW = "6" * 40
GRAPH_PATH = f"targets/{TARGET}/graph.json"
MOVED = "and-reassoc"  # proved at NEW, so it leaves the frontier
FINDING = "finding frontier-lag (F05-R9, D-25, D-35): {}; fix: F05-T10 (Mike, 2026-09-14)"


def move_main(harness: Harness) -> None:
    """``main`` moves: ``and-reassoc`` is proved at ``NEW`` and the three products say so."""
    files = harness.githost.files
    info: dict[str, Any] = json.loads(files["info.json"])
    frontier: dict[str, Any] = json.loads(files["frontier.json"])
    graph: dict[str, Any] = json.loads(files[GRAPH_PATH])
    assert info["rendered_from"] == frontier["rendered_from"] == graph["rendered_from"] == OLD
    info["rendered_from"] = NEW
    frontier["rendered_from"] = NEW
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != MOVED]
    graph["rendered_from"] = NEW
    for node in graph["nodes"]:
        if node["node_id"] == MOVED:
            node["status"], node["proof_commit"] = "proved", NEW
    files["info.json"] = json.dumps(info).encode()
    files["frontier.json"] = json.dumps(frontier).encode()
    files[GRAPH_PATH] = json.dumps(graph).encode()


def frontier_fetches(harness: Harness) -> int:
    return sum(1 for path, _ in harness.githost.fetches if path == "frontier.json")


@pytest.mark.xfail(
    strict=True,
    reason=FINDING.format(
        "after main moves, GET /info.json revalidates and serves the new rendered_from while "
        "GET /frontier.json serves the old commit's frontier from its own cache entry"
    ),
)
def test_the_frontier_follows_info_json_to_the_new_commit(harness: Harness) -> None:
    assert harness.client.get("/info.json").json()["rendered_from"] == OLD
    assert harness.client.get("/frontier.json").json()["rendered_from"] == OLD
    assert frontier_fetches(harness) == 1

    move_main(harness)
    # Guard: inside its window the frontier is still the cached copy, not a refetch.
    assert harness.client.get("/frontier.json").json()["rendered_from"] == OLD
    assert frontier_fetches(harness) == 1

    force_stale(harness, "info.json")
    assert harness.client.get("/info.json").json()["rendered_from"] == NEW, "guard: info moved"

    served = harness.client.get("/frontier.json").json()
    assert served["rendered_from"] == NEW, "the frontier lags info.json by the cache window"
    assert MOVED not in {e["node_id"] for e in served["entries"]}


@pytest.mark.xfail(
    strict=True,
    reason=FINDING.format(
        "over the MCP, server_info shows the new rendered_from while list_frontier and "
        "get_target serve the old commit's frontier and graph"
    ),
)
def test_mcp_reads_follow_server_info_to_the_new_commit(harness: Harness) -> None:
    """Both cache copies: ``list_frontier`` reads through ``frontier.committed`` (via the route)
    and ``get_target`` through ``mcp.reads.committed``."""
    client = McpClient(harness)
    assert client.ok("server_info")["rendered_from"] == OLD
    assert client.ok("list_frontier")["rendered_from"] == OLD
    assert client.ok("get_target", {"target_id": TARGET})["graph"]["rendered_from"] == OLD

    move_main(harness)
    force_stale(harness, "info.json")
    assert client.ok("server_info")["rendered_from"] == NEW, "guard: server_info moved"

    listed = client.ok("list_frontier")
    graph = client.ok("get_target", {"target_id": TARGET})["graph"]
    assert (listed["rendered_from"], graph["rendered_from"]) == (NEW, NEW)
    assert MOVED not in {e["node_id"] for e in listed["entries"]}
    assert next(n for n in graph["nodes"] if n["node_id"] == MOVED)["status"] == "proved"
