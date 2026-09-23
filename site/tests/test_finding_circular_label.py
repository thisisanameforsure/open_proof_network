"""F08-T17: a hole under a merged circularity claim is labelled circular, not offered as work.

Found live 2026-09-23 (``test_finding_circular_decomposition`` in the gate has the account): two
holes on the calibration targets were no easier than the statements they were meant to reduce,
and the site offered each as open work. A merged ``circular-decomposition`` claim now takes such a
node off the frontier with the cause ``circular`` in ``graph.json``; the site must agree — the node
reads "circular", its page says why it is not claimable and links the claim, and the site's set
of workable statements stays the frontier's claimable set (F04-T17's rule).
"""

from __future__ import annotations

import json
import re

import fixture
import pytest
import yaml
from harness import TARGET

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
HOLE = fixture.HOLE  # blocked, cause witness-missing, claimable before the claim
CLAIM = f"targets/{TARGET}/nodes/{HOLE}/defects/20260923T120000Z-alice.yaml"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("circular"))
    doc = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": "circular-decomposition",
        "ancestor": "and-swap-reassoc",
        "line": 1,
        "exhibit": "theorem circular : True → True := id\n",
        "contributor": "alice",
        "date": "2026-09-23",
    }
    (root / CLAIM).parent.mkdir(parents=True)
    (root / CLAIM).write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def lead(page: str) -> str:
    m = re.search(r'<p class="lead">(.*?)</p>', page, re.S)
    assert m is not None, "the node page has no lead paragraph"
    return m.group(1)


def test_the_circular_hole_is_not_work_and_the_site_agrees_with_the_frontier(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, _pages = built
    frontier = json.loads((site.root / "frontier.json").read_text(encoding="utf-8"))
    claimable = {e["node_id"] for e in frontier["entries"] if e["claimable"]}
    assert HOLE not in claimable
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    assert r.node_state(tv.nodes[HOLE]) not in render.WORKABLE_STATES
    workable = {nid for nid, nv in tv.nodes.items() if r.node_state(nv) in render.WORKABLE_STATES}
    assert workable == claimable


def test_the_node_page_says_circular_and_links_the_claim(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{HOLE}/index.html"]
    words = lead(page)
    assert "circular" in words, words
    assert "witness" not in words, "the witness is not the obstacle any more"
    assert "Not claimable" in page
    assert f"/blob/{fixture.COMMIT}/{CLAIM}" in page, "the page names the claim it rests on"


def test_status_mark_says_circular_whatever_the_status() -> None:
    for status in ("ready", "blocked"):
        mark = render.Renderer.status_mark(status, cause="circular")
        assert "circular" in mark and "open" not in mark.split("</span>")[-2], mark
