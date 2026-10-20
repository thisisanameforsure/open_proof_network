"""F04-T54 (D-25 v3.45), part 1: a node's literature status is drawn on every statement graph
as a mark distinct from the proof status, keyed in the drawing's own key, and feeds nothing.

The owner read erdos-1094 against the literature (2026-10-19): eleven statements carry a
``known`` proposal and the open core carries none, and nothing on the drawing showed which
was which. The mark is a small square inside the pill's top-right corner, hollow and dashed
while only proposed, filled once a steward or curator has confirmed it, coloured by status
(three colours that are not the proof-status colours); a node with no record carries no mark;
the key names every state the mark can take, with the words ``literature_words`` uses; the
layout, the frontier views, the selector and the sets table are byte-identical with and
without the fields; and a ``known`` statement is never drawn as done — nothing is in Lean.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_finding_literature_status import literature_dir_allowed  # noqa: F401 — the layout rule

from opn_site import dag, model, one_view, render

REPO = "https://github.com/example/graph"
API = "https://api.example.test"
ROOT = "and-swap-reassoc"  # confirmed known (a dispute of an `open` proposal)
DEP = "and-reassoc"  # proposed open
NONE = "tutorial-and-swap"  # no record
STATIC = Path(render.__file__).resolve().parent / "static"
CSS = (STATIC / "site.css").read_text(encoding="utf-8")
STATUSES = tuple(render.LITERATURE_WORDS)
#: Every mark the renderer can emit: each status the words know, proposed and confirmed.
EVERY_MARK = [
    dag.LitMark(status, confirmed, "someone") for status in STATUSES for confirmed in (False, True)
]


def mark_classes(svg: str) -> set[tuple[str, str]]:
    """Each literature mark in a drawing, as (status, phase) read from its own classes."""
    return set(re.findall(r'<g class="lit-mark lit-([a-z]+) (proposed|confirmed)"', svg))


def with_literature(tmp_path: Path) -> Path:
    """The fixture tree with a confirmed ``known`` on the root that disputes an ``open``
    proposal, an ``open`` proposal on the dep, and nothing on the tutorial node."""
    root = fixture.build(tmp_path)
    proposal = fixture.write_literature(
        root, ROOT, status="open", contributor="t1009-b", date="2026-10-09T12:51:37Z"
    )
    reading = fixture.write_literature(
        root,
        ROOT,
        status="known",
        contributor="mike",
        date="2026-10-19T09:00:00Z",
        summary="Konyagin proved it in 1999.",
        signed=True,
    )
    dep_proposal = fixture.write_literature(
        root, DEP, status="open", contributor="t1009-c", date="2026-10-09T14:48:17Z"
    )
    fixture.publish_v335(
        root,
        literature={
            ROOT: {
                "status": "known",
                "record": reading,
                "contributor": "mike",
                "confirmed_by": "mike",
                "confirmation": reading,
                "disputes": {"status": "open", "record": proposal, "contributor": "t1009-b"},
            }
        },
        literature_proposed={
            DEP: {"status": "open", "record": dep_proposal, "contributor": "t1009-c"}
        },
    )
    return root


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = with_literature(tmp_path_factory.mktemp("marks"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO, api_url=API)


def drawing_of(page: str) -> str:
    m = re.search(r'<svg class="dag"(.*?)</svg>', page, re.S)
    assert m is not None
    return m.group(0)


def legend_of(page: str) -> str:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert m is not None, "the problem page has no graph key"
    return m.group(1)


# --- the mark -----------------------------------------------------------------------------------


def test_a_pill_carries_a_mark_for_its_status_and_phase_and_none_without_a_record(
    pages: dict[str, str],
) -> None:
    svg = drawing_of(pages[f"problems/{TARGET}/index.html"])
    pills = dict(re.findall(r'<g class="node[^"]*" data-node="([^"]+)"(.*?)</g></a>', svg, re.S))
    assert 'class="lit-mark lit-known confirmed"' in pills[ROOT]
    assert 'class="lit-mark lit-open proposed"' in pills[DEP]
    assert "lit-mark" not in pills[NONE]
    assert mark_classes(svg) == {("known", "confirmed"), ("open", "proposed")}


def test_the_marks_title_says_the_status_who_and_whether_it_awaits(pages: dict[str, str]) -> None:
    svg = drawing_of(pages[f"problems/{TARGET}/index.html"])
    assert "<title>Literature: known (confirmed by mike)</title>" in svg
    assert "<title>Literature: open (proposed by t1009-c, awaits confirmation)</title>" in svg


def test_the_mark_is_inside_the_pill_and_clear_of_the_label_halo_and_outline_tab() -> None:
    """In the SVG's own units: the square's box lies within the rect; the label ends at
    ``w - 18`` (F04-T12), the halo is centred at ``(w - 14, 18)`` with radius 3, the outline
    tab hangs outside the rect (``y`` from -7)."""
    for w in (80, 120, 300):
        out = dag.literature_mark(dag.LitMark("known", False, "x"), w)
        m = re.search(r'transform="translate\((\d+),(\d+)\)"', out)
        assert m is not None
        x, y = int(m.group(1)), int(m.group(2))
        assert x > 0 and x + dag.LIT_MARK < w
        assert y > 0 and y + dag.LIT_MARK < dag.NODE_H
        assert x >= w - 18, "the mark sits past the label's end"
        assert y + dag.LIT_MARK < 18 - 3, "the mark sits above the halo"
        assert x + dag.LIT_MARK < w - 8, "the mark sits left of the outline tab"
    assert dag.literature_mark(None, 100) == ""


def test_the_mark_escapes_what_it_is_given() -> None:
    out = dag.literature_mark(dag.LitMark('k"<b>', False, "<i>x</i>"), 100)
    assert "<b>" not in out and "<i>" not in out and '"<' not in out


def test_a_known_statement_keeps_its_own_status_and_is_not_drawn_as_done(
    pages: dict[str, str],
) -> None:
    """Nothing is in Lean: the pill keeps its status class and colour; the mark is an extra."""
    svg = drawing_of(pages[f"problems/{TARGET}/index.html"])
    root_pill = re.search(rf'<g class="(node[^"]*)" data-node="{ROOT}"', svg)
    assert root_pill is not None
    assert "status-ready" in root_pill.group(1) and "proved" not in root_pill.group(1)
    assert not re.search(r"\.dag \.lit-[a-z]+[^{]*\{[^}]*opacity", CSS), "a mark must not mute"
    assert not re.search(r"\.dag \.node\.lit-", CSS), "the status is never keyed on the mark"


# --- the layout and everything else is unchanged ---------------------------------------------


def test_the_layout_is_identical_with_and_without_the_marks(tmp_path: Path) -> None:
    root = with_literature(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    rows = tv.graph["nodes"]
    bare = [
        {k: v for k, v in n.items() if k not in ("literature", "literature_proposed")} for n in rows
    ]
    assert dag.layout(rows, root=tv.root, prefix=TARGET) == dag.layout(
        bare, root=tv.root, prefix=TARGET
    )
    href = {str(n["node_id"]): "/x/" for n in rows}
    marks = render.Renderer(site, repo_url=REPO, decisions_doc=None).literature_marks(tv)
    marked = dag.svg(rows, href=href, root=tv.root, literature=marks)
    unmarked = dag.svg(bare, href=href, root=tv.root)
    assert marked != unmarked
    assert re.sub(r'<g class="lit-mark.*?</g> ', "", marked, flags=re.S) == unmarked


def test_the_views_selector_table_and_layouts_are_byte_identical_without_the_fields(
    tmp_path: Path,
) -> None:
    """D-25: the status feeds nothing — not the routes, the sets, the frontier views, the
    selector or the layouts; only the pills' markup differs, by the marks alone."""
    root = with_literature(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    entries = [e for e in site.frontier["entries"] if e["target_id"] == TARGET]
    bare_graph = dict(tv.graph)
    bare_graph["nodes"] = [
        {k: v for k, v in n.items() if k not in ("literature", "literature_proposed")}
        for n in tv.graph["nodes"]
    ]
    bare_entries = [
        {k: v for k, v in e.items() if k not in ("literature", "literature_proposed")}
        for e in entries
    ]
    href = {nid: "/x/" for nid in tv.nodes}
    with_marks = one_view.drawing(
        tv.graph, entries, href=href, prefix=TARGET, literature=r.literature_marks(tv)
    )
    without = one_view.drawing(bare_graph, bare_entries, href=href, prefix=TARGET)
    assert with_marks.selector == without.selector
    assert with_marks.table == without.table
    assert with_marks.layouts_json == without.layouts_json
    assert with_marks.marks == without.marks and with_marks.sets == without.sets
    assert re.sub(r'<g class="lit-mark.*?</g> ', "", with_marks.svg, flags=re.S) == without.svg
    # The listing's rows: the same words, order and claimability; the badge is the only change.
    marked_rows = r.statement_rows(tv)
    bare_tv = dataclasses.replace(
        tv,
        graph=bare_graph,
        nodes={
            nid: dataclasses.replace(nv, literature=None, literature_proposed=None)
            for nid, nv in tv.nodes.items()
        },
    )
    assert re.sub(r'<span class="lit-badge.*?</span>', "", marked_rows, flags=re.S) == (
        r.statement_rows(bare_tv)
    )


# --- the key -------------------------------------------------------------------------------------


def test_the_key_names_each_state_the_drawing_shows_with_the_literature_words(
    pages: dict[str, str],
) -> None:
    key = legend_of(pages[f"problems/{TARGET}/index.html"])
    items = re.findall(r'<span class="lit-badge lit-([a-z]+) (proposed|confirmed)"', key)
    assert sorted(items) == [("known", "confirmed"), ("open", "proposed")]
    assert render.literature_words("known") in key and render.literature_words("open") in key
    assert "confirmed by a steward or curator" in key
    assert "awaiting a steward or curator" in key
    assert render.literature_words("elementary") not in key, "a state the drawing lacks"


def test_a_drawing_with_no_record_has_no_literature_items_in_its_key(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).target(site.targets[TARGET])
    assert "lit-badge" not in legend_of(page) and "lit-mark" not in drawing_of(page)


def test_every_mark_the_renderer_can_emit_is_named_in_the_key() -> None:
    """The guard (the 2026-09-24 lesson): iterate the *outputs* — every class
    ``literature_mark`` can put on a pill — and hold the key to each, so a status added to the
    words cannot slip past the key."""
    key = render.Renderer.literature_key(EVERY_MARK)
    for mark in EVERY_MARK:
        out = dag.literature_mark(mark, 100)
        (status, phase), *_ = re.findall(r'class="lit-mark lit-([a-z]+) (proposed|confirmed)"', out)
        item = re.search(
            rf'<span class="term[^"]*" tabindex="0"><span class="lit-badge lit-{status} {phase}">'
            rf"</span>([^<]+)<span class=\"term-card\" role=\"tooltip\">(.*?)</span></span>",
            key,
            re.S,
        )
        assert item is not None, (status, phase)
        assert item.group(1).strip() == f"{status}, {phase}"
        assert render.esc(render.literature_words(status)) in item.group(2)
        assert ("confirmed by" if mark.confirmed else "awaiting") in item.group(2)
    assert key.count("lit-badge") == len(EVERY_MARK)


def test_the_stylesheet_colours_every_status_apart_from_the_proof_colours() -> None:
    """Three tokens, none the proof-status colours (accent, warn, bad, select, the greys);
    the drawing's mark and the key's badge share them; proposed is dashed, confirmed filled."""
    tokens = {s: re.search(rf"--lit-{s}: (#[0-9a-f]{{6}});", CSS) for s in STATUSES}
    assert all(tokens.values()), tokens
    colours = {s: m.group(1).lower() for s, m in tokens.items() if m}
    assert len(set(colours.values())) == len(STATUSES)
    used = {
        m.lower()
        for m in re.findall(
            r"--(?:accent[-0-9]*|warn|bad|select|n[0-9]{3}|proved|ready): (#[0-9a-f]{6})", CSS
        )
    }
    assert not set(colours.values()) & used
    for s in STATUSES:
        assert re.search(rf"\.lit-{s}\b", CSS), s
    assert re.search(r"\.dag \.lit-mark\.proposed rect \{[^}]*stroke-dasharray", CSS)
    assert re.search(r"\.dag \.lit-mark\.confirmed rect \{[^}]*fill: var\(--lit\)", CSS)
    assert re.search(r"\.lit-badge\.proposed \{[^}]*dashed", CSS)


# --- the listing row and the node page's head -------------------------------------------------


def test_the_listing_row_and_the_node_head_carry_the_same_badge(pages: dict[str, str]) -> None:
    listing = pages["problems/index.html"]
    rows = dict(
        re.findall(
            r'<div class="stmt"[^>]*>(.*?)<a href="/nodes/propositional/([^/]+)/"', listing, re.S
        )
    )
    # The row: badge after the state word, title with the words; none for a node with no record.
    row_of = {nid: body for body, nid in rows.items()}
    assert re.search(
        r'<span class="lit-badge lit-known confirmed" '
        r'title="Literature: known \(confirmed by mike\)"',
        listing,
    )
    assert "lit-badge" not in row_of.get(NONE, "lit-badge")  # the tutorial row has none
    head = re.search(
        r'<header class="node-head">(.*?)</header>', pages[f"nodes/{TARGET}/{DEP}/index.html"], re.S
    )
    assert head is not None
    assert (
        '<span class="lit-badge lit-open proposed" title="Literature: open (proposed by t1009-c, '
        'awaits confirmation)"></span>'
    ) in head.group(1)
    none_head = re.search(
        r'<header class="node-head">(.*?)</header>',
        pages[f"nodes/{TARGET}/{NONE}/index.html"],
        re.S,
    )
    assert none_head is not None and "lit-badge" not in none_head.group(1)


def test_the_badge_escapes_the_contributors_name(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    rel = fixture.write_literature(
        root, DEP, status="known", contributor="x", date="2026-10-09T14:48:17Z"
    )
    fixture.publish_v335(
        root,
        literature_proposed={DEP: {"status": "known", "record": rel, "contributor": '"><b>x'}},
    )
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    badge = r.lit_badge(site.targets[TARGET].nodes[DEP])
    assert "<b>" not in badge and '"><b>' not in badge and "&quot;&gt;&lt;b&gt;x" in badge


def test_marks_are_read_from_the_views_the_confirmed_status_first() -> None:
    """A node with a confirmed status and a later proposal is marked by the fact (the block
    says the proposal); a proposal alone is marked proposed; no record, no mark."""
    base: dict[str, Any] = {"status": "known", "record": "r", "contributor": "c"}
    confirmed = model.LiteratureView(**base, confirmed_by="mike", confirmation="r")
    later = model.LiteratureView(status="elementary", record="r2", contributor="t")
    assert render.lit_mark_of(confirmed, later) == dag.LitMark("known", True, "mike")
    assert render.lit_mark_of(None, later) == dag.LitMark("elementary", False, "t")
    assert render.lit_mark_of(None, None) is None
    bogus = model.LiteratureView(status="unheard-of", record="r", contributor="c")
    assert render.lit_mark_of(None, bogus) is None, "only a status the key can name is drawn"
