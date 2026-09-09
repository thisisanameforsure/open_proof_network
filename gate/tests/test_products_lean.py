"""F03-T3: library tags through the seam (R6; AC12). Lean tier.

AC12 asks for a statement importing two Mathlib namespaces; no graph pins Mathlib before F11 and
the Lake package is Lean-core-only, so the classification is proved on synthetic module names in
``test_products.py`` and the real seam is exercised here on the Mathlib-free fixture, where the
scan must return no tags and the cache must record that (F03-Q6).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness import TARGET, copy_graph

from opn_gate import graph, products
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean


def test_library_tags(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    root = copy_graph(tmp_path)
    tg = graph.load_target(root, TARGET)
    tc = LocalToolchain(real_toolchain.elan, lean_pkg)
    scanned: list[str] = []

    def scanner(node: graph.NodeFacts) -> list[str]:
        scanned.append(node.node_id)
        return products.scan_statement(tc, pinned, node, tmp_path / "scan" / node.node_id)

    # The root's statement imports its Context; the interior ones import nothing.
    for node_id in tg.order:
        assert scanner(tg.nodes[node_id]) == []
    cache = products.TagCache(tg.path / products.TAGS_CACHE)
    assert cache.tags(tg.nodes["and-reassoc"], scanner) == [] and cache.dirty
    (tg.path / products.TAGS_CACHE).write_bytes(cache.rendered())
    reloaded = products.TagCache(tg.path / products.TAGS_CACHE)
    before = len(scanned)
    assert reloaded.tags(tg.nodes["and-reassoc"], scanner) == [] and len(scanned) == before
    assert json.loads((tg.path / products.TAGS_CACHE).read_text()) == {
        tg.nodes["and-reassoc"].statement_hash: []
    }
