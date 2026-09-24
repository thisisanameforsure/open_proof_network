"""F08-T20 (D-12 v3.22): the ancestor a circularity claim circles back to names the claim.

The ancestor stays open and claimable — it is the problem, and the circle says only that one
route to it made no progress — so its page must say so, link the claim, and invite a direct proof
or a different decomposition. The nodes strictly between it and the claimed hole read circular and
link the same claim, which sits under a node other than their own. The site reads the gate's own
``graph.circular_marks`` so the two cannot disagree about which nodes a claim reaches.
"""

from __future__ import annotations

import re

import fixture
import pytest
from harness import TARGET
from test_finding_circular_path import CLAIM, DEEP, PATH, ROOT, claimed

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = claimed(tmp_path_factory.mktemp("circular-path"))
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def claim_url() -> str:
    return f"{REPO}/blob/{fixture.COMMIT}/{CLAIM}"


def test_the_ancestors_page_names_the_claim_and_invites_other_routes(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, pages = built
    assert site.targets[TARGET].nodes[ROOT].circular_below == (CLAIM,)
    page = pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    m = re.search(r'<p class="circular-note">(.*?)</p>', page, re.S)
    assert m is not None, "the ancestor's page carries no circularity note"
    note = m.group(1)
    assert claim_url() in note, "the note links the claim"
    assert "direct proof" in note and "different decomposition" in note
    assert "Not claimable" not in page, "the ancestor stays claimable"
    assert page.count(claim_url()) >= 2, "the note links the claim and the footer lists it (R2)"


def test_the_ancestors_panel_on_the_problem_page_carries_the_note(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"problems/{TARGET}/index.html"]
    panels = dict(
        re.findall(
            r'<div class="card panel" data-node="([^"]+)"(.*?)(?=<div class="card panel"|$)',
            page,
            re.S,
        )
    )
    assert set(panels) >= {ROOT, *PATH}, "guard: the problem page has a panel per statement"
    assert 'class="circular-note"' in panels[ROOT]
    assert claim_url() in panels[ROOT]
    assert all('class="circular-note"' not in panels[n] for n in PATH)


@pytest.mark.parametrize("node_id", PATH)
def test_a_path_node_reads_circular_and_links_the_claim_under_the_hole(
    built: tuple[model.Site, dict[str, str]], node_id: str
) -> None:
    site, pages = built
    nv = site.targets[TARGET].nodes[node_id]
    assert nv.cause == "circular"
    assert nv.circular_claim == CLAIM, "the claim sits under the hole, not under this node"
    page = pages[f"nodes/{TARGET}/{node_id}/index.html"]
    assert "Not claimable" in page
    assert claim_url() in page
    assert "its defects/" not in page


def test_the_hole_itself_is_unchanged(built: tuple[model.Site, dict[str, str]]) -> None:
    site, pages = built
    assert site.targets[TARGET].nodes[DEEP].circular_claim == CLAIM
    assert claim_url() in pages[f"nodes/{TARGET}/{DEEP}/index.html"]
