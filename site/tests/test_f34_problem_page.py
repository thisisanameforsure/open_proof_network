"""F34-T11 (R13, R19; handoff §3.4.1, §3.4.5): the problem page in the handoff's order, nothing on
it dropped.

* The order: the statement as the headline, its status and stage mark, one sentence on its
  stewards and open statements, then "On this page" and the numbered sections — §1 Proof, §3 The
  statement and its review, §4 Stewards, panel and write-up, §5 What is known and tried, §6 Record
  (§2, Not on a route, is T18's).
* Nothing dropped (``New-Problem-InfoMap``): every fragment today's page was built from still
  renders, verbatim, on the new page — two by the owner's word excepted: the follow-the-proof
  toggle (F34-Q7) and the definition modules' Lean, which is linked, never printed (R19).
* A problem with no work shows "What this problem needs" in place of the routes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import fixture
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"


def builds() -> list[tuple[str, Callable[..., Any]]]:
    return [
        ("curated", fixture.build),
        ("stewards", fixture.build_with_stewards),
        ("qa", fixture.build_with_qa_target),
    ]


@pytest.fixture(scope="module", params=builds(), ids=lambda b: b[0])
def built(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> tuple[render.Renderer, dict[str, str]]:
    _name, build = request.param
    root = build(tmp_path_factory.mktemp(f"f34-problem-{_name}"))
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO)
    return r, render.render_site(site, repo_url=REPO)


def fragments(r: render.Renderer, tv: Any) -> dict[str, str]:
    """What today's page was built from, by name: each must render on the new page."""
    picture = r.problem_drawing(tv)
    return {
        "status": r.status_tag(tv),
        "fidelity": r.fidelity_tag(tv),
        "review state": r.review_state_tag(tv),
        "informal": r.informal_words(tv),
        "source line": r.source_line(tv),
        "claimable": r.target_claimable(tv),
        "calibration": r.calibration_label(tv),
        "registrations": r.registration_lines(tv),
        "steward card": r.steward_card(tv),
        "legend": r.graph_legend(tv, picture),
        "drawing": picture.svg,
        "band": picture.band,
        "panels": "".join(r.statement_panel(tv, nv) for nv in r.ordered_nodes(tv)),
        "digestion": r.digestion_section(tv),
        "proved in words": r.proved_in_words(tv),
        "stewards": r.stewards_section(tv),
        "panel": r.panel_section(tv),
        "write-up": r.writeup_section(tv),
        "sources": r.sources_block(tv),
        "qa block": r.qa_block(tv),
        "informal full": r.informal_line(tv),
        "qa": r.qa_section(tv),
        "review sentence": render.esc(r.review_sentence(tv)),
        "fast check": render.esc(r.fast_check(tv.index_entry.get("mathlib_sha"))),
        "stage words": r.stage_marks(tv),
    }


def test_nothing_on_the_page_is_dropped(built: tuple[render.Renderer, dict[str, str]]) -> None:
    r, pages = built
    for tid, tv in r.site.targets.items():
        page = pages[f"problems/{tid}/index.html"]
        missing = [name for name, html in fragments(r, tv).items() if html and html not in page]
        assert missing == [], (tid, missing)


def test_the_sections_are_numbered_in_order(built: tuple[render.Renderer, dict[str, str]]) -> None:
    r, pages = built
    for tid in r.site.targets:
        page = pages[f"problems/{tid}/index.html"]
        heads = re.findall(r'<h2 id="([a-z-]+)"><span class="sec">§(\d)</span> ([^<]+)</h2>', page)
        assert [(sid, n) for sid, n, _w in heads] == [
            ("proof", "1"),
            ("statement", "3"),
            ("people", "4"),
            ("known", "5"),
            ("record", "6"),
        ], (tid, heads)
        nav = re.search(r'<nav class="onpage"[^>]*>(.*?)</nav>', page, re.S)
        assert nav is not None, tid
        for sid, _n, _w in heads:
            assert f'href="#{sid}"' in nav.group(1), (tid, sid)


def test_the_head_is_the_statement_with_its_mark_and_one_sentence(
    built: tuple[render.Renderer, dict[str, str]],
) -> None:
    r, pages = built
    for tid, tv in r.site.targets.items():
        page = pages[f"problems/{tid}/index.html"]
        head = page[page.index('<section class="problem-head">') : page.index("</section>")]
        assert r.informal_words(tv) in head and r.stage_mark(tv) in head, tid
        sentence = re.search(r'<p class="head-sentence">(.*?)</p>', head, re.S)
        assert sentence is not None, tid
        open_ = r.open_count(tv)
        assert f"{open_} statement{'' if open_ == 1 else 's'} open" in sentence.group(1), tid


def test_definitions_are_linked_never_printed(tmp_path_factory: pytest.TempPathFactory) -> None:
    root = fixture.build_with_qa_target(tmp_path_factory.mktemp("f34-defs"))
    site = model.load_site(root, fixture.COMMIT)
    pages = render.render_site(site, repo_url=REPO)
    for tid, tv in site.targets.items():
        page = pages[f"problems/{tid}/index.html"]
        assert '<pre class="lean definition' not in page and 'class="definition"' not in page
        for f in tv.definitions:
            assert f"{REPO}/blob/{fixture.COMMIT}/{f.path}" in page, (tid, f.path)
        if tv.definitions:
            assert re.search(r"<details class=\"defs\"><summary>Shared definitions \(\d+\)", page)


def test_a_problem_with_no_work_says_what_it_needs(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-needs"))
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO)
    pages = render.render_site(site, repo_url=REPO)
    waiting = [tid for tid, tv in site.targets.items() if not r.has_work(tv)]
    assert waiting, "guard: the fixture has a problem waiting for a steward"
    for tid in waiting:
        card = re.search(
            r'<div class="needs-card">(.*?)</div>', pages[f"problems/{tid}/index.html"], re.S
        )
        assert card is not None, tid
        assert "A steward." in card.group(1) and f'href="/steward/{tid}/"' in card.group(1)
    worked = pages[f"problems/{TARGET}/index.html"]
    assert 'class="needs-card"' not in worked
