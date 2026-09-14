"""F05-T10: one freshness generation for every committed file (F05-R9; C7).

``info.json``'s ETag is the marker. ``test_finding_frontier_lag`` holds the defect it fixes;
these hold the edges: an unchanged marker (a 304) invalidates nothing and costs no other fetch,
an unreachable marker invalidates nothing and every entry keeps its last good copy, a first
request on an empty cache works through both ``committed()`` copies, and the marker is checked
at most once per window however many files a window reads. Directory listings
(``list_dir``, path ending in ``/``) are not cached and are left out of every count.
"""

from __future__ import annotations

import json
import time

from api_fakes import Harness
from mcp_client import TARGET, McpClient
from test_finding_frontier_lag import GRAPH_PATH, NEW, OLD, move_main
from test_frontier import force_stale

from opn_api import frontier, info
from opn_api.mcp import reads as mcp_reads

INFO = "info.json"
INDEX = "targets/index.json"  # unchanged by move_main


def reads(harness: Harness) -> list[tuple[str, str | None]]:
    """The file fetches, without directory listings."""
    return [(p, etag) for p, etag in harness.githost.fetches if not p.endswith("/")]


def warm(harness: Harness) -> McpClient:
    """Cache the marker, the frontier, the target graph (MCP copy) and the index (route copy)."""
    client = McpClient(harness)
    assert harness.client.get("/info.json").json()["rendered_from"] == OLD
    assert harness.client.get("/frontier.json").json()["rendered_from"] == OLD
    assert client.ok("get_target", {"target_id": TARGET})["graph"]["rendered_from"] == OLD
    frontier.committed(harness.context, INDEX)
    assert set(harness.context.files) == {INFO, "frontier.json", GRAPH_PATH, INDEX}
    harness.githost.fetches.clear()
    return client


def clocks(harness: Harness) -> dict[str, float]:
    return {p: e.fetched_at for p, e in harness.context.files.items() if p != INFO}


def test_the_marker_is_the_file_info_json_serves() -> None:
    assert info.INFO_PATH == frontier.INFO_PATH


def test_a_first_request_reads_the_marker_then_the_file(harness: Harness) -> None:
    r = harness.client.get("/frontier.json")
    assert r.status_code == 200
    assert r.json()["rendered_from"] == OLD
    assert reads(harness) == [(INFO, None), ("frontier.json", None)]


def test_a_first_mcp_read_reads_the_marker_then_the_file(harness: Harness) -> None:
    graph = McpClient(harness).ok("get_target", {"target_id": TARGET})["graph"]
    assert graph["rendered_from"] == OLD
    assert reads(harness) == [(INFO, None), (GRAPH_PATH, None)]


def test_info_json_is_its_own_marker_and_costs_one_fetch(harness: Harness) -> None:
    harness.client.get("/info.json")
    assert reads(harness) == [(INFO, None)]
    force_stale(harness, INFO)
    harness.client.get("/info.json")
    assert [p for p, _ in reads(harness)] == [INFO, INFO]


def test_the_marker_is_checked_at_most_once_per_window(harness: Harness) -> None:
    client = McpClient(harness)
    for _ in range(3):
        harness.client.get("/frontier.json")
        harness.client.get("/info.json")
        client.ok("get_target", {"target_id": TARGET})
        client.ok("list_frontier")
    assert [p for p, _ in reads(harness)].count(INFO) == 1


def test_an_unchanged_marker_invalidates_nothing(harness: Harness) -> None:
    """A 304 on ``info.json`` renews the marker and no other entry is aged or fetched."""
    client = warm(harness)
    before = clocks(harness)
    force_stale(harness, INFO)

    assert harness.client.get("/frontier.json").json()["rendered_from"] == OLD
    assert client.ok("get_target", {"target_id": TARGET})["graph"]["rendered_from"] == OLD
    frontier.committed(harness.context, INDEX)

    fetched = reads(harness)
    assert [p for p, _ in fetched] == [INFO], "only the marker is asked"
    assert fetched[0][1] is not None, "a conditional GET, answered 304"
    assert clocks(harness) == before


def test_a_moved_marker_ages_every_entry_and_each_revalidates_by_its_own_etag(
    harness: Harness,
) -> None:
    client = warm(harness)
    etags = {p: e.etag for p, e in harness.context.files.items()}
    index_body = harness.context.files[INDEX].body
    move_main(harness)
    force_stale(harness, INFO)

    assert harness.client.get("/info.json").json()["rendered_from"] == NEW
    window = harness.settings.frontier_max_stale_s
    now = time.monotonic()
    assert all(now - at > window for at in clocks(harness).values()), "every other entry is stale"

    assert harness.client.get("/frontier.json").json()["rendered_from"] == NEW
    assert client.ok("get_target", {"target_id": TARGET})["graph"]["rendered_from"] == NEW
    assert frontier.committed(harness.context, INDEX) == index_body  # unchanged: a 304

    assert reads(harness) == [
        (INFO, etags[INFO]),
        ("frontier.json", etags["frontier.json"]),
        (GRAPH_PATH, etags[GRAPH_PATH]),
        (INDEX, etags[INDEX]),
    ]
    assert harness.context.files[INDEX].etag == etags[INDEX]
    assert harness.context.files["frontier.json"].etag != etags["frontier.json"]


def test_an_mcp_read_alone_finds_that_main_moved(harness: Harness) -> None:
    """The MCP copy runs the generation check itself: with no ``/info.json`` or ``/frontier.json``
    read in between, ``get_target`` is the first to see the marker move and still follows it.
    (The finding test reads ``server_info`` first, so it cannot tell whether this copy checks.)"""
    client = warm(harness)
    move_main(harness)
    force_stale(harness, INFO)
    graph = client.ok("get_target", {"target_id": TARGET})["graph"]
    assert graph["rendered_from"] == NEW
    assert [p for p, _ in reads(harness)] == [INFO, GRAPH_PATH]


def test_an_unreachable_marker_invalidates_nothing_and_serves_the_last_good_copies(
    harness: Harness,
) -> None:
    """C7: main moved, but the host cannot say so; every read keeps its last good copy and no
    entry is aged. When the host answers again, the generation moves them all."""
    client = warm(harness)
    before = clocks(harness)
    move_main(harness)
    harness.githost.unreachable = True
    force_stale(harness, INFO)

    assert harness.client.get("/info.json").json()["rendered_from"] == OLD
    assert harness.client.get("/frontier.json").json()["rendered_from"] == OLD
    # The MCP copy directly: get_target also lists a directory, which is uncached and is
    # rightly an error while the host is down (F09-R10).
    graph = mcp_reads.committed(harness.context, GRAPH_PATH)
    assert graph is not None
    assert json.loads(graph)["rendered_from"] == OLD
    assert clocks(harness) == before
    assert {p for p, _ in reads(harness)} == {INFO}, "only the marker is retried"

    harness.githost.unreachable = False
    assert harness.client.get("/frontier.json").json()["rendered_from"] == NEW
    assert client.ok("get_target", {"target_id": TARGET})["graph"]["rendered_from"] == NEW


def test_a_graph_without_info_json_still_serves_its_other_files(harness: Harness) -> None:
    """A marker the graph does not have is an unreadable marker, not an outage of the file
    being read: the frontier and the MCP reads still answer."""
    del harness.githost.files[INFO]
    assert harness.client.get("/frontier.json").status_code == 200
    graph = McpClient(harness).ok("get_target", {"target_id": TARGET})["graph"]
    assert graph["rendered_from"] == OLD
    assert harness.client.get("/info.json").status_code == 503
