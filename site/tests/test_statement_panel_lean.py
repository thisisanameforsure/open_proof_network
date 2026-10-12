"""F04-T42: every statement panel on a problem page carries its Lean.

A reader of the live erdos-1094 page reported three panels with no Lean in them. It did not
reproduce: the panel template writes ``<pre class="lean statement">`` unconditionally and the
renderer fills it from the node's ``Statement.lean``. This is a guard, not a red test: it holds
that, for every panel on the fixture problem page, the block is there, is not empty, and carries
the node's own ``theorem`` line, so a later change that drops or empties it fails here.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import fixture
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
PAGE = f"problems/{TARGET}/index.html"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    root = fixture.build(tmp_path_factory.mktemp("panel-lean"))
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    return root, pages[PAGE]


def panels(page: str) -> dict[str, str]:
    """Each statement panel's markup, keyed by its ``data-node``."""
    starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r'<div class="card panel" data-node="([^"]+)"', page)
    ]
    out = {}
    for i, (start, node) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(page)
        out[node] = page[start:end]
    return out


def theorem_line(root: Path, node: str) -> str:
    text = (root / "targets" / TARGET / "nodes" / node / "Statement.lean").read_text("utf-8")
    return next(line for line in text.splitlines() if line.startswith("theorem "))


def test_every_panel_carries_its_nodes_theorem(built: tuple[Path, str]) -> None:
    root, page = built
    found = panels(page)
    nodes = sorted(p.name for p in (root / "targets" / TARGET / "nodes").iterdir() if p.is_dir())
    assert sorted(found) == nodes, "guard: one panel per node of the target"
    for node, panel in found.items():
        m = re.search(r'<pre class="lean statement[^"]*">(.*?)</pre>', panel, re.S)
        assert m is not None, f"{node}: no Lean block in its panel"
        lean = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
        assert lean.strip(), f"{node}: the Lean block is empty"
        assert theorem_line(root, node) in lean, (node, lean[:200])
