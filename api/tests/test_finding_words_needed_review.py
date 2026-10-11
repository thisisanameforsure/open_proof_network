"""F22-T7 (testers 2026-10-06, request D and P3-13): ``list_words_needed`` says what is already
being written and which nodes are superseded.

W1, W2 and W3 each picked a file from the list, wrote its words and were refused
``duplicate-submission`` because another writer's pull request was open on it; W1 also wrote for
``erdos-1050--h1``, a node superseded by ``h1-v2``, because the list did not say so. Each row now
carries ``in_review`` — ``{pr_number, author}`` of the open words pull request that can still
merge on that subject, joined through the ``words:`` fingerprint the one-writer rule reads, or
null — and ``node_status``, the node's status in the target's ``graph.json`` (null for a
definition module). Rows of superseded nodes come last, each target's order otherwise kept.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import serve
from test_mcp_words_needed import PLAIN
from test_mcp_words_needed import rendered as rendered_graph

from opn_api.mcp import results

rendered = rendered_graph  # the words tests' two rendered targets, built once per module


@pytest.fixture
def tree(rendered: Path, tmp_path: Path) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(rendered, root)
    return root


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    harness = make_harness()
    serve(harness, tree)
    with harness.client:
        yield harness


GLOSS_FAILED = [{"name": "gate", "status": "completed", "conclusion": "failure", "url": "r"}]


def rows(h: Harness) -> list[dict[str, object]]:
    out = McpClient(h).ok("list_words_needed", {})
    assert results.violations("list_words_needed", out) == [], out
    return list(out["subjects"])


def statement_row(h: Harness, subjects: list[dict[str, object]]) -> dict[str, object]:
    """A statement row of the plain target whose node id no other target uses: the fixture's
    two targets share node ids, and the route finds a node by its id alone."""
    elsewhere = {
        n["node_id"]
        for path, raw in h.githost.files.items()
        if path.endswith("/graph.json") and not path.startswith(f"targets/{PLAIN}/")
        for n in json.loads(raw).get("nodes", [])
    }
    return next(
        r
        for r in subjects
        if r["target"] == PLAIN and r["kind"] == "statement" and r["node"] not in elsewhere
    )


def test_every_row_says_its_node_status_and_nobody_reviews_it(h: Harness) -> None:
    subjects = rows(h)
    assert subjects
    for row in subjects:
        assert row["in_review"] is None, row
        if row["kind"] == "definition":
            assert row["node_status"] is None, row
        else:
            assert isinstance(row["node_status"], str), row


def test_a_subject_in_an_open_pull_request_names_it(h: Harness) -> None:
    target = statement_row(h, rows(h))
    body = {
        "subject": {"kind": "statement", "node_id": target["node"]},
        "text": "Words being written.",
        "licence": "CC-BY-4.0",
    }
    r = h.client.post("/glosses", json=body, headers=h.auth(h.token_for("code_bob", "bob")))
    assert r.status_code == 201, r.text
    row = next(x for x in rows(h) if x["file"] == target["file"])
    assert row["in_review"] == {"pr_number": r.json()["pr_number"], "author": "bob"}
    others = [x for x in rows(h) if x["file"] != target["file"]]
    assert all(x["in_review"] is None for x in others)
    # a pull request whose gate failed blocks nothing, and is not "in review" here either
    h.githost.set_pull_request_state(r.json()["pr_number"], runs=GLOSS_FAILED)
    h.context.pulls.clear()
    row = next(x for x in rows(h) if x["file"] == target["file"])
    assert row["in_review"] is None


def test_superseded_nodes_are_marked_and_listed_last(h: Harness) -> None:
    subjects = rows(h)
    victim = statement_row(h, subjects)["node"]
    path = f"targets/{PLAIN}/graph.json"
    graph = json.loads(h.githost.files[path])
    for node in graph["nodes"]:
        if node["node_id"] == victim:
            node["status"] = "superseded"
    h.githost.files[path] = json.dumps(graph).encode()
    h.context.files.clear()
    h.context.listings.clear()
    after = rows(h)
    flags = [r["node_status"] == "superseded" for r in after]
    assert any(flags), after
    assert flags == sorted(flags), "superseded rows come last"
    marked = {(r["target"], r["node"]) for r in after if r["node_status"] == "superseded"}
    assert marked == {(PLAIN, victim)}
    kept = [r["file"] for r in after if r["node_status"] != "superseded"]
    expected = [r["file"] for r in subjects if (r["target"], r["node"]) != (PLAIN, victim)]
    assert kept == expected, "order otherwise kept"
