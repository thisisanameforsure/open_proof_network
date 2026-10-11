"""Finding served-rendered-from (testers 2026-10-09, B3): a fresh hole's products name a commit
that does not hold the hole.

The post-merge job writes a merged partial's holes and renders the products in one bot commit,
labelled with the merge commit it rendered from, which has no hole directories. The guide tells an
HTTP client to read a node's files on the raw host at ``GET /frontier.json``'s ``rendered_from``,
so every freshly written hole was a 404 there until the next merge on its target re-rendered
(``get_node erdos-1094--h2--h1`` named ``93c88d5``; the hole arrived in ``54630ba8``). The guide
already said the service's ``rendered_from`` is the commit it read the tree at; nothing did that.
The service reads every file at ``main``'s sha (F05-T13), so that is the commit it names: on the
frontier, on ``info.json``, and on ``get_node``'s bundle, whose files are read there too. The
committed products keep their own label, and a precheck is still pinned by it (F06-Q10, Q19).
"""

from __future__ import annotations

import json

from api_fakes import Harness
from mcp_client import NODE, NODE_DIR, McpClient
from test_mcp_equivalence import seed_graph

from opn_api import frontier, precheck

HEAD = "b" * 40


def committed_label(harness: Harness) -> str:
    label = json.loads(harness.githost.files["frontier.json"])["rendered_from"]
    assert label != HEAD, "guard: the committed products name an older commit than main"
    return str(label)


def test_served_rendered_from_is_mains_sha(harness: Harness) -> None:
    label = committed_label(harness)
    harness.githost.head = HEAD
    assert harness.client.get("/frontier.json").json()["rendered_from"] == HEAD
    assert harness.client.get("/info.json").json()["rendered_from"] == HEAD
    assert frontier.committed_frontier(harness.context)["rendered_from"] == label


def test_get_node_names_and_reads_at_mains_sha(harness: Harness) -> None:
    seed_graph(harness)
    harness.githost.head = HEAD
    harness.githost.refs.clear()
    harness.githost.fetches.clear()
    node = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert node["context"]["rendered_from"] == HEAD
    own = {
        ref
        for (path, _), ref in zip(harness.githost.fetches, harness.githost.refs, strict=True)
        if path.startswith(NODE_DIR)
    }
    assert own == {HEAD}, "a node's files are read at the commit it names"


def test_without_a_head_the_committed_label_is_served(harness: Harness) -> None:
    """C7: when the API cannot say where ``main`` is, the service reads at the branch and names
    what the products say."""
    label = committed_label(harness)
    harness.githost.head_failure = "boom"
    assert harness.client.get("/frontier.json").json()["rendered_from"] == label


def test_a_precheck_is_still_pinned_by_the_committed_label(harness: Harness) -> None:
    label = committed_label(harness)
    harness.githost.head = HEAD
    harness.client.get("/frontier.json")
    assert precheck.rendered_from(harness.context) == label
