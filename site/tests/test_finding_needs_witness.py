"""F04-T17: a hole waiting only for its witness is open work, and the site says so (Q19).

Found by an outside contributor on the live ``erdos-69`` page, 2026-09-18. ``frontier.json``
listed 29 entries, all claimable, seven of them holes whose one obstacle is an unfilled witness
slot (``blocked``, cause ``witness-missing``; F03-T9 put them on the frontier because the witness
*is* the work, D-29). The site counted 22 open statements, called those seven "Not accepting
work", labelled their action "Blocked", and its masthead's "Work on a statement" filter hid a
problem whose only work was a witness — while the Problems page's footnote said the frontier
"lists exactly the open statements shown here". The contributor supplied a witness anyway, by
reading sibling nodes; the service accepted it and the gate passed it.

The site's rule was the gate's rule of 2026-09-10 (``ready`` or ``speculative``). It now names the
third case, and these tests hold the site's set of workable statements to the frontier's.
"""

from __future__ import annotations

import json
import re

import fixture
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
PROBLEM = f"problems/{TARGET}/index.html"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("witness"))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def row(page: str, node_id: str) -> str:
    rows = re.findall(r'<div class="stmt".*?</div>', page, flags=re.S)
    hits = [r for r in rows if f"/{node_id}/" in r]
    assert len(hits) == 1, (node_id, len(hits))
    return str(hits[0])


def test_the_sites_workable_statements_are_the_frontiers(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """One set, two readers: what the site invites work on is what a claim can take."""
    site, _pages = built
    frontier = json.loads((site.root / "frontier.json").read_text(encoding="utf-8"))
    claimable = {e["node_id"] for e in frontier["entries"] if e["claimable"]}
    assert fixture.HOLE in claimable and fixture.REVISION in claimable, "guard: the fixture"
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    workable = {nid for nid, nv in tv.nodes.items() if r.node_state(nv) in render.WORKABLE_STATES}
    assert workable == claimable
    assert r.open_count(tv) == len(claimable)


def test_a_hole_awaiting_its_witness_reads_as_work(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    stmt = row(pages["problems/index.html"], fixture.HOLE)
    assert 'data-state="needs-witness"' in stmt and 'data-workable="1"' in stmt
    assert "needs a witness" in stmt and "Supply a witness →" in stmt
    assert "Not accepting work" not in stmt and ">Blocked<" not in stmt


def test_a_superseded_hole_is_not_work(built: tuple[model.Site, dict[str, str]]) -> None:
    """Its slot is as empty as its successor's, and it owes nobody a witness (D-8)."""
    _site, pages = built
    stmt = row(pages["problems/index.html"], fixture.REVISED_HOLE)
    assert 'data-state="superseded"' in stmt and 'data-workable="0"' in stmt
    assert "Supply a witness" not in stmt


def test_the_counts_include_witness_work(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert '<span class="n">3</span>' in pages["problems/index.html"]  # root, hole, revision
    card = re.search(r'<article class="card problem"[^>]*>', pages["problems/index.html"])
    assert card and 'data-open="3"' in card.group(0)
    assert "3 open statements" in pages["index.html"]


def test_the_filter_keeps_every_workable_row() -> None:
    script = (render.STATIC / "problems.js").read_text(encoding="utf-8")
    assert 'getAttribute("data-workable") === "1"' in script
    assert 'getAttribute("data-state") === "open"' not in script


def test_the_panel_offers_the_witness_as_the_work(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    panels = pages[PROBLEM].split('<div class="card panel" ')[1:]
    panel = next(p for p in panels if p.startswith(f'data-node="{fixture.HOLE}"'))
    assert "Supply a witness" in panel and "View the record" not in panel
    assert "needs a witness" in panel


def test_the_glossary_defines_the_witness_and_the_state(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    for key in ("witness", "needs-witness"):
        assert key in render.GLOSSARY_BY_KEY, key
    docs = pages["docs/index.html"]
    assert "needs a witness" in docs and "named <code>witness</code>" not in docs  # escaped prose
    meaning = render.GLOSSARY_BY_KEY["witness"][1]
    assert "named witness" in meaning and "∃" in meaning and "True" in meaning
    assert "Not accepting work" not in render.GLOSSARY_BY_KEY["needs-witness"][1]
    # The blocked row no longer speaks for a hole: it waits on other statements.
    assert "witness" in render.GLOSSARY_BY_KEY["blocked"][1]


def test_the_footnote_claims_only_what_is_true(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert "lists exactly the open statements" not in pages["problems/index.html"]
    assert "lists every open statement shown here" in pages["problems/index.html"]


def test_the_graph_key_names_the_state_when_a_statement_has_it(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    after = pages[PROBLEM].split('<div class="dag-legend">', 1)[1]
    legend = after.split('<div class="dag-scroll">')[0]
    assert "needs a witness" in legend and 'class="dot dot-needs-witness"' in legend
    assert 'class="node status-needs-witness"' in pages[PROBLEM]
