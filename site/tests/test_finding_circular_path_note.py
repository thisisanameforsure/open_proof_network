"""F08-T20 (D-12 v3.22), restated for D-12 v3.35 (F04-T37): one claim labels the whole path.

A merged circularity claim on the deepest hole of a chain whose other holes are proved speaks of
every node strictly between the hole and its ancestor (v3.22's path rule). Since v3.35 what it
says is a label — *a proof of this statement is a proof of <ancestor>* — carried on each such
row by the products, and no node leaves the frontier for it. The ancestor stays open and its
page still names the claim (``circular_below``, a route that circles back); the path nodes carry
the label naming the ancestor and link the claim, which sits under the hole, not under them. The
site reads the rows the gate wrote, so it cannot reach a different set of nodes than the products.
"""

from __future__ import annotations

import json
import re

import fixture
import pytest
from harness import TARGET
from test_finding_circular_decomposition import file_claim
from test_finding_circular_path import CLAIM, CLAIM_REF, DEEP, PATH, ROOT, chain

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
LABELLED = (*PATH, DEEP)
LABEL_RE = re.compile(r'<p class="circular-label">(.*?)</p>', re.S)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    """The chain's products rendered before the claim (the claim removes nothing), the claim
    filed, then the rows rewritten with the label the v3.35 gate derives for the path."""
    root = chain(tmp_path_factory.mktemp("circular-path"))
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    file_claim(root, CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    label = [{"ancestor": ROOT, "claim": CLAIM_REF}]
    fixture.publish_v335(root, circular=dict.fromkeys(LABELLED, label))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def claim_url() -> str:
    return f"{REPO}/blob/{fixture.COMMIT}/{CLAIM}"


def test_the_ancestors_page_names_the_claim_and_invites_other_routes(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, pages = built
    assert site.targets[TARGET].nodes[ROOT].circular_below == (CLAIM,)
    assert site.targets[TARGET].nodes[ROOT].circular == ()
    page = pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    m = re.search(r'<p class="circular-note">(.*?)</p>', page, re.S)
    assert m is not None, "the ancestor's page carries no circularity note"
    note = m.group(1)
    assert claim_url() in note, "the note links the claim"
    assert "direct proof" in note and "different decomposition" in note
    assert "no progress" not in note, "v3.35: the claim says nothing about progress"
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
    assert set(panels) >= {ROOT, *LABELLED}, "guard: the problem page has a panel per statement"
    assert 'class="circular-note"' in panels[ROOT]
    assert claim_url() in panels[ROOT]
    assert all('class="circular-note"' not in panels[n] for n in LABELLED)
    assert all('class="circular-label"' in panels[n] for n in LABELLED)


@pytest.mark.parametrize("node_id", LABELLED)
def test_a_path_node_carries_the_label_naming_the_ancestor_and_stays_work(
    built: tuple[model.Site, dict[str, str]], node_id: str
) -> None:
    site, pages = built
    nv = site.targets[TARGET].nodes[node_id]
    assert nv.cause != "circular"
    assert nv.circular == (model.CircularLabel(ancestor=ROOT, claim=CLAIM),)
    page = pages[f"nodes/{TARGET}/{node_id}/index.html"]
    assert "Not claimable" not in page
    labels = LABEL_RE.findall(page)
    assert len(labels) == 1
    assert f'<a href="/nodes/{TARGET}/{ROOT}/">{ROOT}</a>' in labels[0]
    assert claim_url() in labels[0]
    assert "its defects/" not in page
    frontier = json.loads((site.root / "frontier.json").read_text(encoding="utf-8"))
    row = next(e for e in frontier["entries"] if e["node_id"] == node_id)
    assert row["needs"] in ("proof", "witness"), "the frontier still offers it as work"
    r = render.Renderer(site, repo_url=REPO)
    assert r.node_state(nv) in render.WORKABLE_STATES
