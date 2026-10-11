"""F21-T7 / AC7: ``list_words_needed`` (R8; D-28 notation note of 2026-10-05, Q6).

The tool reads each target's committed ``glosses.json`` and ``target.yaml`` at main's head and
answers every subject that lacks words — target, file, kind, node, reason and, for a proof, the
outline's path — by the gate's own ``glosses.needed``. Its answer equals the uncovered rows of
``opn-gate gloss coverage`` on the same tree, Context files aside; it filters by target and by
kind with equality only, names a filter it does not know, and ranks nothing (D-25).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from harness import GRAPH
from mcp_client import McpClient
from test_gloss_coverage import (
    ALTERNATE,
    HOLE,
    PARTIAL,
    ROOT,
    TARGET,
    VARIANT,
    _as_v1,
    curated_graph,
    explain,
    gloss,
    nodes,
)
from test_glosses_route import serve

from opn_api import frontier
from opn_api.mcp import bijection, results
from opn_gate import glosses, products, schemas

COMMIT = "5" * 40
HEAD = "7" * 40
PLAIN = "propositional"  # the second target: no target.yaml, so its root needs a gloss
KEEP = ("target", "file", "kind", "node", "module", "reason")


def render(root: Path) -> None:
    """Every product, as the post-merge job writes them."""
    prod = products.generate(root, rendered_from=COMMIT, commit_time="2026-10-06T00:00:00Z")
    prod.write(root)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two targets: the coverage tests' curated one, part way through getting its words (a
    witness glossed, a gloss of since-changed text, an explained partial, a definition
    glossed), and the plain propositional one. Rendered once; each test copies it."""
    root = curated_graph(tmp_path_factory.mktemp("words"))
    shutil.copytree(GRAPH / "targets" / PLAIN, root / "targets" / PLAIN)
    schemas.publish(root)
    gloss(root, "witness", ROOT)
    gloss(root, "witness", HOLE)
    (nodes(root) / HOLE / "Witness.lean").write_text("theorem witness : True := trivial\n")
    gloss(root, "definition", None, "Primes.lean")
    explain(root, ROOT, PARTIAL)
    render(root)
    return root


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


def uncovered(tree: Path) -> list[dict[str, Any]]:
    """``gloss coverage``'s uncovered rows, Context files aside, by file."""
    rows = [
        {k: r[k] for k in KEEP}
        for r in glosses.coverage(tree)["subjects"]
        if not r["covered"] and r["kind"] != "context"
    ]
    return sorted(rows, key=lambda r: str(r["file"]))


def bare(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(({k: r[k] for k in KEEP} for r in rows), key=lambda r: str(r["file"]))


def test_the_tool_is_a_read_with_its_plain_paths(h: Harness) -> None:
    listed = {t.name: t for t in McpClient(h).list_tools()}
    tool = listed["list_words_needed"]
    assert tool.outputSchema == results.declared("list_words_needed")  # F09-T20
    assert tool.annotations is not None and tool.annotations.readOnlyHint is True
    row = bijection.BY_TOOL["list_words_needed"]
    assert row.kind == "read" and row.routes == ()
    assert "targets/<id>/glosses.json" in row.graph_paths
    assert "targets/<id>/target.yaml" in row.graph_paths


def test_the_rows_equal_coverage(h: Harness, tree: Path) -> None:
    """AC7: every subject lacking words, on every target, is coverage's uncovered row (Context
    aside), with the reason coverage gives; a proof names its outline's path."""
    out = McpClient(h).ok("list_words_needed", {})
    assert results.violations("list_words_needed", out) == []
    expected = uncovered(tree)
    assert {r["target"] for r in expected} == {TARGET, PLAIN}, "guard: both targets lack words"
    assert bare(out["subjects"]) == expected
    assert out["count"] == len(expected) and out["unread"] == []
    reasons = {r["file"]: r["reason"] for r in out["subjects"]}
    base = f"targets/{TARGET}"
    assert reasons[f"{base}/nodes/{HOLE}/Witness.lean"] == "describes-earlier-text"
    assert reasons[f"{base}/nodes/{ROOT}/{ALTERNATE}"] == "no-explainer"
    assert f"{base}/nodes/{ROOT}/{PARTIAL}" not in reasons  # explained
    assert f"{base}/nodes/{ROOT}/Statement.lean" not in reasons  # the curated informal words
    assert reasons[f"targets/{PLAIN}/nodes/and-swap-reassoc/Statement.lean"] == (
        "root-without-informal"
    )
    [proof] = [r for r in out["subjects"] if r["file"] == f"{base}/nodes/{ROOT}/{ALTERNATE}"]
    digest = schemas.content_hash((nodes(tree) / ROOT / ALTERNATE).read_bytes())
    assert proof["outline"] == f"{base}/outlines/{digest}.json"
    assert all(r["outline"] is None for r in out["subjects"] if r["kind"] == "statement")
    # The record's order, target by target as the index lists them: nothing is ranked (D-25).
    index = json.loads((tree / "targets" / "index.json").read_bytes())
    order = [t["target_id"] for t in index["targets"]]
    seen = list(dict.fromkeys(r["target"] for r in out["subjects"]))
    assert seen == [t for t in order if t in seen]
    for target in seen:
        product = json.loads((tree / "targets" / target / "glosses.json").read_bytes())
        files = [f"targets/{target}/{s['file']}" for s in product["subjects"]]
        mine = [r["file"] for r in out["subjects"] if r["target"] == target]
        assert mine == [f for f in files if f in mine]


def test_filters_by_target_and_kind(h: Harness, tree: Path) -> None:
    client = McpClient(h)
    expected = uncovered(tree)
    one = client.ok("list_words_needed", {"target_id": PLAIN})
    assert one["target_id"] == PLAIN
    assert bare(one["subjects"]) == [r for r in expected if r["target"] == PLAIN]
    proofs = client.ok("list_words_needed", {"kind": "alternate"})
    assert bare(proofs["subjects"]) == [r for r in expected if r["kind"] == "alternate"] != []
    both = client.ok("list_words_needed", {"target_id": TARGET, "kind": "statement"})
    assert bare(both["subjects"]) == [
        r for r in expected if r["target"] == TARGET and r["kind"] == "statement"
    ]
    assert {r["node"] for r in both["subjects"]} == {HOLE, VARIANT}
    for doc in (one, proofs, both):
        assert results.violations("list_words_needed", doc) == []
        assert doc["count"] == len(doc["subjects"])


def test_an_unknown_kind_is_named(h: Harness) -> None:
    refused = McpClient(h).failed("list_words_needed", {"kind": "lemma"})
    assert refused["error"] == "filter-unknown" and refused["source"] == "adapter"
    assert "lemma" in refused["message"] and "statement" in refused["message"]
    assert results.violations("list_words_needed", refused) == []


def test_a_target_not_on_the_graph_is_named(h: Harness) -> None:
    refused = McpClient(h).failed("list_words_needed", {"target_id": "no-such-target"})
    assert refused["error"] == "not-found" and refused["source"] == "graph"
    assert "no-such-target" in refused["message"]
    assert results.violations("list_words_needed", refused) == []


def test_reads_at_mains_head(h: Harness, tree: Path) -> None:
    """F05-T13: the products are read at the commit main is at, not at the branch path the
    host's CDN caches. The branch path still holds the old product; the head has the new one
    (the alternate now explained), and the answer follows the head."""
    explain(tree, ROOT, ALTERNATE)
    render(tree)
    path = f"targets/{TARGET}/glosses.json"
    h.githost.files_at[HEAD] = {path: (tree / path).read_bytes()}
    h.githost.head = HEAD
    frontier.expire(h.context)
    out = McpClient(h).ok("list_words_needed", {"target_id": TARGET})
    assert out["read_at"] == HEAD
    assert not any(r["kind"] == "alternate" for r in out["subjects"]), out["subjects"]
    assert bare(out["subjects"]) == [r for r in uncovered(tree) if r["target"] == TARGET]
    assert HEAD in h.githost.refs


def test_an_unrendered_or_older_product(h: Harness, tree: Path) -> None:
    """A target whose ``glosses.json`` is not on the graph (a graph rendered before F20) is
    named under ``unread``, never answered as having nothing to write, and the others are still
    answered; a ``glosses/v1`` product, which the live graph holds until its re-pin, reads."""
    path = f"targets/{PLAIN}/glosses.json"
    del h.githost.files[path]
    v1 = _as_v1(json.loads((tree / f"targets/{TARGET}/glosses.json").read_bytes()))
    h.githost.files[f"targets/{TARGET}/glosses.json"] = schemas.canonical_json(v1)
    h.context.files.clear()
    out = McpClient(h).ok("list_words_needed", {})
    assert results.violations("list_words_needed", out) == []
    [unread] = out["unread"]
    assert unread["target"] == PLAIN and unread["path"] == path
    assert bare(out["subjects"]) == [r for r in uncovered(tree) if r["target"] == TARGET]
