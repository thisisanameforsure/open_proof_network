"""D-12 v3.35 (F04-T37): a merged circularity claim labels the hole and removes nothing.

F08-T17 (2026-09-23) took a hole under a merged ``circular-decomposition`` claim off the frontier
with the cause ``circular``, and this file pinned that: the node read "circular", its page said
"Not claimable". The erdos-1094 run (2026-10-08) showed the claim's exhibit is met by every honest
reduction and by the last open hole of any decomposition, so decisions v3.35 made the claim a
published fact — *a proof of this statement is a proof of <ancestor>* — carried on the row as
``circular: [{ancestor, claim}]`` (``graph/v6``, ``frontier/v5``). The hole stays claimable.

The site renders status and claimability from the products alone (a labelled node is open like
any other), shows the label on the node page and on the problem page's row and panel, with the
claim linked at the commit, and its workable set still equals the frontier's claimable set
(F04-T17's rule). The retired cause ``circular`` on an older snapshot (D-34) changes no state.
"""

from __future__ import annotations

import dataclasses
import json
import re

import fixture
import pytest
import yaml
from harness import TARGET

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
HOLE = fixture.HOLE  # blocked, cause witness-missing: on the frontier, needs a witness
ANCESTOR = "and-swap-reassoc"
CLAIM_FILE = "20260923T120000Z-alice.yaml"
CLAIM_REF = f"{HOLE}/defects/{CLAIM_FILE}"  # relative to the target's nodes/, as the row says
CLAIM = f"targets/{TARGET}/nodes/{CLAIM_REF}"
LABEL_RE = re.compile(r'<p class="circular-label">(.*?)</p>', re.S)


def file_claim(root: object) -> None:
    doc = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": "circular-decomposition",
        "ancestor": ANCESTOR,
        "line": 1,
        "exhibit": "theorem circular : True → True := id\n",
        "contributor": "alice",
        "date": "2026-09-23",
    }
    path = root / CLAIM  # type: ignore[operator]
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    """The revised-hole fixture, its products rendered, then the claim filed and the products
    rewritten as the v3.35 gate writes them: the hole's row carries the label, nothing else
    changes (the claim removes nothing)."""
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("circular"))
    file_claim(root)
    fixture.publish_v335(root, circular={HOLE: [{"ancestor": ANCESTOR, "claim": CLAIM_REF}]})
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def lead(page: str) -> str:
    m = re.search(r'<p class="lead">(.*?)</p>', page, re.S)
    assert m is not None, "the node page has no lead paragraph"
    return m.group(1)


def claim_url() -> str:
    return f"{REPO}/blob/{fixture.COMMIT}/{CLAIM}"


def test_the_labelled_hole_is_work_and_the_site_agrees_with_the_frontier(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """(a) Status and claimability come from the products alone: the frontier lists the hole as
    work, so the site does; the workable set is the frontier's."""
    site, _pages = built
    frontier = json.loads((site.root / "frontier.json").read_text(encoding="utf-8"))
    assert frontier["schema"] == "frontier/v5"
    rows = {e["node_id"]: e for e in frontier["entries"]}
    assert HOLE in rows and rows[HOLE]["circular"] == [{"ancestor": ANCESTOR, "claim": CLAIM_REF}]
    claimable = {
        e["node_id"] for e in frontier["entries"] if e["claimable"] or e["needs"] == "witness"
    }
    assert HOLE in claimable
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    assert r.node_state(tv.nodes[HOLE]) in render.WORKABLE_STATES
    workable = {nid for nid, nv in tv.nodes.items() if r.node_state(nv) in render.WORKABLE_STATES}
    assert workable == claimable


def test_the_model_reads_the_label_from_the_row(built: tuple[model.Site, dict[str, str]]) -> None:
    site, _pages = built
    nv = site.targets[TARGET].nodes[HOLE]
    assert nv.circular == (model.CircularLabel(ancestor=ANCESTOR, claim=CLAIM),)
    assert nv.circular_claim == CLAIM, "the first label's claim, for the pages that link one"
    other = site.targets[TARGET].nodes[ANCESTOR]
    assert other.circular == ()


def test_the_node_page_shows_the_label_and_stays_open(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """(b), (e): one neutral line per entry of ``circular``, the ancestor and the claim linked;
    no sentence calls the node circular, not claimable, or no progress."""
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{HOLE}/index.html"]
    words = lead(page)
    assert "circular" not in words, words
    assert "Not claimable" not in page
    assert "no progress" not in page and "leads straight back" not in page
    labels = LABEL_RE.findall(page)
    assert len(labels) == 1, page
    label = labels[0]
    assert "A proof of this statement is a proof of" in label
    assert f'<a href="/nodes/{TARGET}/{ANCESTOR}/">{ANCESTOR}</a>' in label
    assert claim_url() in label, "the claim is linked at the rendered commit"
    assert page.count(claim_url()) >= 2, "the footer lists the claim among the files rendered"


def test_the_problem_page_row_and_panel_carry_the_label(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """(b), (d): the listing's row says it, in a form a filter can key on; the statement's panel
    carries the same line, the ancestor linked to its own panel."""
    _site, pages = built
    listing = pages["problems/index.html"]  # the listing's rows; the panels are the problem page's
    rows = re.findall(r'<div class="stmt" data-state="[a-z-]+"(.*?)</div>', listing, re.S)
    assert len(rows) == len(_site.targets[TARGET].nodes), "guard: one row per statement"
    row = next(r for r in rows if f"/nodes/{TARGET}/{HOLE}/" in r)
    assert 'data-circular="1"' in row
    # The visible words (the hover cards aside): the state is the status's, then the label.
    text = row.split(">", 1)[1]  # past the row's own attributes
    shown = re.sub(
        r"<[^>]+>", "", re.sub(r'<span class="term-card".*?</span>', "", text, flags=re.S)
    )
    assert f"proves {ANCESTOR}" in shown, shown
    assert "needs a witness" in shown and "circular" not in shown.lower(), shown
    others = [r for r in rows if f"/nodes/{TARGET}/{HOLE}/" not in r]
    assert others and all('data-circular="0"' in r for r in others)
    page = pages[f"problems/{TARGET}/index.html"]
    panels = dict(
        re.findall(
            r'<div class="card panel" data-node="([^"]+)"(.*?)(?=<div class="card panel"|$)',
            page,
            re.S,
        )
    )
    label = LABEL_RE.findall(panels[HOLE])
    assert len(label) == 1 and f'<a href="#node={ANCESTOR}">{ANCESTOR}</a>' in label[0]
    assert claim_url() in label[0]
    assert "Not claimable" not in panels[HOLE]
    assert 'class="circular-label"' not in panels[ANCESTOR]


def test_the_retired_cause_changes_no_state() -> None:
    """D-34: an older snapshot's rows still say ``cause: circular``; since v3.35 that is a label
    the products no longer write, never a state, so the words and the state are the status's."""
    mark = render.Renderer.status_mark("ready", cause="circular")
    assert "open" in mark and "circular" not in mark, mark
    assert render.status_words("blocked", "circular") == render.STATUS_WORDS["blocked"]
    assert "circular" not in render.CAUSE_WORDS


def test_an_older_graph_derives_the_label_from_the_tree(tmp_path: object) -> None:
    """A ``graph/v5`` snapshot has no ``circular`` field; the site reads the merged claim files
    through the gate's own reader, as F08-T17 did, and a node with no claim reads no label."""
    root = fixture.build_with_revised_hole(tmp_path / "old")  # type: ignore[operator]
    file_claim(root)
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    graph = json.loads((root / "targets" / TARGET / "graph.json").read_text(encoding="utf-8"))
    assert graph["schema"] == "graph/v5" and "circular" not in graph["nodes"][0]
    nv = site.targets[TARGET].nodes[HOLE]
    assert nv.circular == (model.CircularLabel(ancestor=ANCESTOR, claim=CLAIM),)
    assert site.targets[TARGET].nodes["and-reassoc"].circular == ()
    # And a row carrying the retired cause is drawn by its status, not as circular.
    r = render.Renderer(site, repo_url=REPO)
    entry = {**nv.graph_entry, "status": "ready", "cause": "circular"}
    assert r.node_state(dataclasses.replace(nv, graph_entry=entry)) == "open"
