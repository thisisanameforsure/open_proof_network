"""F04-T14 (Q16): the statement graph's key sits inside the graph card, encodes every status the
graph shows, and defines each item on hover.

The finding (Mike, 2026-09-18, erdos-402): the key ``proved · open · blocked`` sat in the section
head, directly above the "Selected statement" card, and read as that statement's status; a stale
root and two superseded holes wore the same neutral dot as a blocked node, so the page had no way
to say what they were.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
ROOT = "and-swap-reassoc"
DEP = "and-reassoc"
STATIC = Path(render.__file__).resolve().parent / "static"


def page(tmp_path: Path, statuses: dict[str, str] | None = None) -> str:
    """The fixture's problem page, with the named nodes' statuses replaced."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    nodes = dict(tv.nodes)
    for node_id, status in (statuses or {}).items():
        nv = nodes[node_id]
        nodes[node_id] = dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": status})
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return r.target(dataclasses.replace(tv, nodes=nodes))


def legend(html: str) -> str:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', html, re.S)
    assert m is not None, "the problem page has no graph key"
    return m.group(1)


def legend_words(html: str) -> list[str]:
    return re.findall(r'<span class="dot dot-[a-z]+"></span>([a-z ]+)<span class="term-card"', html)


def test_the_key_is_inside_the_graph_card(tmp_path: Path) -> None:
    html = page(tmp_path)
    head = re.search(r'<div class="section-head">(.*?)<div class="graph-grid">', html, re.S)
    assert head is not None
    assert "dot-proved" not in head.group(1), "the key still sits above the selected statement"
    assert "mini-legend" not in html
    card = html.index('<div class="dag-wrap card">')
    assert card < html.index('<div class="dag-legend">') < html.index("<svg")


def test_the_key_always_names_the_three_base_states(tmp_path: Path) -> None:
    assert legend_words(legend(page(tmp_path))) == ["proved", "open", "blocked"]


def test_the_key_names_the_other_statuses_the_graph_shows(tmp_path: Path) -> None:
    html = page(tmp_path, {ROOT: "stale", DEP: "superseded"})
    assert legend_words(legend(html)) == ["proved", "open", "blocked", "stale", "superseded"]


def test_a_speculative_node_reads_open_in_the_key(tmp_path: Path) -> None:
    """The site's word for a claimable status is "open" (F03-Q8); the key adds no second word."""
    html = page(tmp_path, {ROOT: "speculative"})
    assert legend_words(legend(html)) == ["proved", "open", "blocked"]


@pytest.mark.parametrize("status", sorted(render.LEGEND_EXTRA))
def test_each_key_item_defines_itself_on_hover(tmp_path: Path, status: str) -> None:
    html = legend(page(tmp_path, {ROOT: status}))
    _word, meaning, proto = render.GLOSSARY_BY_KEY[status]
    item = (
        f'<span class="term" tabindex="0"><span class="dot dot-{status}"></span>{status}'
        f'<span class="term-card" role="tooltip">{render.esc(meaning)}'
        f'<span class="proto">protocol: {render.esc(proto)}</span></span></span>'
    )
    assert item in html


def test_every_status_the_gate_can_derive_has_a_key_entry() -> None:
    """A status with no entry would fall back to the neutral dot and no definition — the defect."""
    for status in render.STATUS_WORDS:
        key = "open" if status in render.CLAIMABLE_STATUSES else status
        assert key in render.GLOSSARY_BY_KEY, status
        assert key in ("proved", "open", "blocked") or key in render.LEGEND_EXTRA, status


def test_the_selected_statement_panel_wears_its_own_dot(tmp_path: Path) -> None:
    html = page(tmp_path, {ROOT: "stale"})
    panel = re.search(rf'<div class="card panel" data-node="{ROOT}".*?</div>', html, re.S)
    assert panel is not None
    assert '<dd><span class="dot dot-stale"></span>stale</dd>' in panel.group(0)


def test_the_problems_page_row_defines_a_stale_statement(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes[ROOT]
    stale = dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": "stale"})
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    hover = r.state_hover(stale)
    assert 'class="dot dot-stale"' in hover
    assert render.esc(render.GLOSSARY_BY_KEY["stale"][1]) in hover


def test_the_stylesheet_colours_every_key_entry() -> None:
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    for status in render.LEGEND_EXTRA:
        assert f".dot-{status}" in css, status
        assert f".dag .status-{status} circle" in css, status
    # the hover card must not be clipped by the graph's own scroll container
    wrap = re.search(r"^\.dag-wrap \{[^}]*\}", css, re.M)
    assert wrap is not None and "overflow" not in wrap.group(0)
    assert re.search(r"^\.dag-scroll \{[^}]*overflow-x: auto", css, re.M)


def test_the_docs_glossary_carries_the_new_words(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    docs, _files = render.Renderer(site, repo_url=REPO, decisions_doc=None).docs()
    for status in render.LEGEND_EXTRA:
        assert render.esc(render.GLOSSARY_BY_KEY[status][1]) in docs, status
