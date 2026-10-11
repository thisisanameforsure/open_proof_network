"""F19-T8 (R8, R10, R11; AC7, AC8): the reading view, one page per way a problem is proved.

The erdos-1050 shape: the root's proof uses one node, which uses one more (root → h1-v2 → h3, a
chain by use). Here the fixture's root uses ``and-reassoc``, whose proof uses
``tutorial-and-swap``, so dependencies first is tutorial-and-swap, and-reassoc, root — the reverse
of the graph's lexical record order, which is what makes the order a test of the rule. The page
leads with the problem's statement and its QA state, then each node of the proof's closure with
its Lean statement, its gloss slot, its explainer (or the recruiting cue) and its outline folded to
top-level steps, then a table from each node to its declaration, lines and attestation.
"""

from __future__ import annotations

import dataclasses
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import reading_fixture as rf
from harness import TARGET

from opn_site import model, render

ROOT, MIDDLE, LEAF = "and-swap-reassoc", "and-reassoc", "tutorial-and-swap"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = rf.chain_tree(tmp_path_factory.mktemp("reading"))
    site = model.load_site(root, rf.COMMIT)
    return site, render.render_site(site, repo_url=rf.REPO)


def reading_page(site: model.Site, pages: dict[str, str]) -> str:
    [proof] = site.targets[TARGET].graph["target_proofs"]
    path = rf.reading_path(TARGET, proof["artifact_hash"])
    assert path in pages, f"no reading view at {path}"
    return pages[path]


def test_dependency_order_statement_first_and_table(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, pages = built
    page = reading_page(site, pages)
    nodes = re.findall(r'<li class="rv-node"[^>]*data-node="([^"]+)"', page)
    assert nodes == [LEAF, MIDDLE, ROOT]
    # The problem's statement and its QA state come before every node.
    first_node = page.index('<li class="rv-node"')
    statement = page.index('class="rv-statement"')
    assert statement < first_node
    assert "fidelity mechanical-only" in page[statement:first_node]
    # The correspondence table: one row per node, in the same order, each linking its attestation.
    table = re.search(r'<table class="correspondence">.*?</table>', page, re.S)
    assert table is not None
    rows = re.findall(r'<tr data-node="([^"]+)">(.*?)</tr>', table.group(0), re.S)
    assert [n for n, _ in rows] == [LEAF, MIDDLE, ROOT]
    for node_id, row in rows:
        assert re.search(r'href="[^"]*/attestations/\d{6}\.json"', row), node_id
        assert re.search(rf"nodes/{node_id}/Proof\.lean#L1-L\d+", row), node_id
    assert "OpnProp.and_reassoc" in dict(rows)[MIDDLE]
    # A node with no explainer shows the recruiting cue (D-36), and every node a gloss slot.
    middle = re.search(
        rf'<li class="rv-node"[^>]*data-node="{MIDDLE}".*?</li>\s*(?=<li|</ol>)', page, re.S
    )
    assert middle is not None and "No explainer yet" in middle.group(0)
    # F20-T8 (R13): and the problem's own statement at the top carries one too.
    assert len(re.findall(r'data-gloss-slot="', page)) == 4
    # The outline is folded: no step is open.
    assert 'class="proof-outline"' in page and "<details open" not in page
    # The problem page's proof selector leads here.
    assert f'href="{rf.reading_path(TARGET, "")}' in pages[f"problems/{TARGET}/index.html"]


class Blocks(HTMLParser):
    """Each ``data-block`` element, with the text of the block label it opens with."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[tuple[str, str | None]] = []
        self.awaiting: list[int] = []  # indices of blocks whose label has not been seen yet
        self.depth: list[int] = []
        self.in_label = False
        self.label_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("data-block"):
            self.blocks.append((str(a["data-block"]), None))
            self.awaiting.append(len(self.blocks) - 1)
        if tag == "p" and a.get("class") == "block-label" and self.awaiting:
            self.in_label, self.label_text = True, ""

    def handle_data(self, data: str) -> None:
        if self.in_label:
            self.label_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self.in_label:
            self.in_label = False
            i = self.awaiting.pop()
            self.blocks[i] = (self.blocks[i][0], self.label_text)


def labels(page: str) -> list[tuple[str, str | None]]:
    parser = Blocks()
    parser.feed(page)
    return parser.blocks


def test_every_block_has_a_text_label(
    built: tuple[model.Site, dict[str, str]], tmp_path: Path
) -> None:
    """AC8 (R11): every block kind either page can emit opens with its provenance in words."""
    site, pages = built
    reading = labels(reading_page(site, pages))
    # The node page of the outlined tutorial, with an annex, and an acknowledgment planted the way
    # the escaping tests plant one; the root's page carries the partial assemblies.
    root = rf.shoot_root(tmp_path)
    shot = model.load_site(root, rf.COMMIT)
    r = render.Renderer(shot, repo_url=rf.REPO, decisions_doc=None)
    nv = shot.targets[TARGET].nodes[LEAF]
    ack = {"checker": "off-by-one-range", "location": "Statement.lean:3", "justification": "ok"}
    node = labels(r.node(dataclasses.replace(nv, acknowledgments=(ack,))))
    partials = labels(r.node(shot.targets[TARGET].nodes[ROOT]))
    seen = reading + node + partials
    kinds = {k for k, _ in seen}
    assert kinds >= {
        "statement",
        "outline",
        "proof",
        "witness",
        "attestation",
        "explainer",
        "annex",
        "partial",
        "acknowledgment",
        "correspondence",
    }, kinds
    phrases = tuple(render.PROVENANCE.values())
    unlabelled = [(k, t) for k, t in seen if t is None or not t.strip().startswith(phrases)]
    assert unlabelled == []
    # The four R11 words, each where it belongs.
    by_kind = {k: t for k, t in seen if t}
    assert by_kind["explainer"].startswith("Informal account, unverified")
    assert by_kind["annex"].startswith("Untrusted contributor text")
    assert by_kind["outline"].startswith("Checked by the kernel") and "4" * 12 in by_kind["outline"]
    assert any(k == "statement" and t and t.startswith("Statement") for k, t in reading)
