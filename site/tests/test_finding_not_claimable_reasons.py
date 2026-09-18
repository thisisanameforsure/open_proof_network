"""Finding site-not-claimable-reasons (2026-09-13, the Euclid tester): the site says "listed,
listed" and gives the not-claimable reasons on the Targets page only.

The Targets page filled ``$status, $claimable`` with the D-33 status and the words "listed, not
claimable", so a listed target read "listed, listed, not claimable". The reasons
``targets/index.json`` carries (``not_claimable``) appeared in the target card and nowhere a prover
actually lands: the node page and the frontier row of a listed target's node said nothing.

Mike's decision (2026-09-14, plan F04-T10): the node page and the frontier row of a node under a
not-claimable target carry "Not claimable" and each reason in ``intake.explain``'s words.

F04-T12 (the redesign, Q14) merged Targets and Frontier into one Problems page: a problem's card
carries one status tag whose hover card names the reasons, the statement rows carry none, and the
node page is unchanged. The tests below assert that shape.

F14-R1 (2026-09-14) made a listed, unsigned target claimable, so the fixture these tests render is
the listed target with an upstream edit flagged on its root — the reason that still closes
claiming on a curated target that is otherwise open.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from fixture import LISTED_ROOT, LISTED_TARGET
from fixture import build_with_frozen_target as build_with_listed_target  # F14-R1, see above

from opn_gate import intake
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE_PAGE = f"nodes/{LISTED_TARGET}/{LISTED_ROOT}/index.html"


@pytest.fixture(scope="module")
def listed(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[str], dict[str, str]]:
    """The not-claimable reasons of the listed target, and the rendered site."""
    from fixture import COMMIT  # noqa: PLC0415

    root = build_with_listed_target(tmp_path_factory.mktemp("listed"))
    site = model.load_site(root, COMMIT)
    reasons = [str(r) for r in site.targets[LISTED_TARGET].index_entry["not_claimable"]]
    assert reasons, "guard: the listed fixture row names reasons"
    return reasons, render.render_site(site, repo_url=REPO)


def _card(page: str, target_id: str) -> str:
    [card] = [
        c for c in page.split('<article class="card problem"')[1:] if f'id="p-{target_id}"' in c
    ]
    return card.split("</article>", 1)[0]


def _status_tag(card: str) -> str:
    """The status tag with its hover card: the first ``.term.tag`` of the card's id row."""
    start = card.index('<span class="term tag"')
    return card[start : card.index("</span></span>", start)]


def test_problems_card_does_not_say_listed_twice(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    card = _card(listed[1]["problems/index.html"], LISTED_TARGET)
    assert 'data-status="open"' in card, "guard: the listed target's status"
    assert "listed, listed" not in card and "listed" not in _status_tag(card)


def test_node_page_of_a_listed_target_says_why_it_is_not_claimable(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    reasons, pages = listed
    page = pages[NODE_PAGE]
    assert "Not claimable" in page
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in page, reason


def test_the_status_tag_of_a_listed_target_carries_the_reasons(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    """The reasons live in the status tag's hover card (Q14), once per card, and nowhere in the
    statement rows."""
    reasons, pages = listed
    card = _card(pages["problems/index.html"], LISTED_TARGET)
    tag = _status_tag(card)
    assert "Not claimable: " in tag
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in tag, reason
    assert card.count("Not claimable") == 1
    rows = card.split('<div class="statements">', 1)[1]
    assert "Not claimable" not in rows


# --- edge cases (the card's status tag) --------------------------------------------------------


def _site_and_node(tmp_path: Path) -> tuple[model.Site, model.NodeView]:
    from fixture import COMMIT  # noqa: PLC0415

    site = model.load_site(build_with_listed_target(tmp_path), COMMIT)
    return site, site.targets[LISTED_TARGET].nodes[LISTED_ROOT]


def _with_entry(site: model.Site, **fields: object) -> model.Site:
    tv = site.targets[LISTED_TARGET]
    entry = {**tv.index_entry, **fields}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    return dataclasses.replace(site, targets=targets)


def test_a_reason_carrying_html_is_escaped_in_the_status_tag(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    payload = '<script>alert(1)</script>"x'
    page = render.Renderer(
        _with_entry(site, not_claimable=[payload]), repo_url=REPO, decisions_doc=None
    ).problems()
    assert "<script>alert" not in page
    assert render.esc(payload) in _status_tag(_card(page, LISTED_TARGET))


def test_an_empty_reasons_list_still_says_not_claimable_in_the_tag(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    page = render.Renderer(
        _with_entry(site, claimable=False, not_claimable=[]), repo_url=REPO, decisions_doc=None
    ).problems()
    assert "Not claimable: this target has no curated intake record (D-6)" in _status_tag(
        _card(page, LISTED_TARGET)
    )


def test_a_claimable_card_carries_no_reasons(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    page = render.Renderer(
        _with_entry(site, claimable=True, not_claimable=[]), repo_url=REPO, decisions_doc=None
    ).problems()
    card = _card(page, LISTED_TARGET)
    assert "Not claimable" not in card and 'data-status="open"' in card


def test_a_stewardless_card_reads_needs_a_steward(tmp_path: Path) -> None:
    """The one reason with a status word of its own (Vocabulary): the tag reads "needs a
    steward" and its card still names the reason."""
    site, _nv = _site_and_node(tmp_path)
    page = render.Renderer(
        _with_entry(site, claimable=False, not_claimable=[intake.NO_STEWARD]),
        repo_url=REPO,
        decisions_doc=None,
    ).problems()
    card = _card(page, LISTED_TARGET)
    assert 'data-status="needs a steward"' in card
    assert render.esc(intake.explain(intake.NO_STEWARD)) in _status_tag(card)


def test_a_proved_card_carries_no_reasons(tmp_path: Path) -> None:
    """A proved problem's tag says proved; "the target's D-33 status is resolved" is not a
    reason a reader needs (Q14)."""
    site, _nv = _site_and_node(tmp_path)
    page = render.Renderer(
        _with_entry(site, status="resolved", claimable=False, not_claimable=["status-resolved"]),
        repo_url=REPO,
        decisions_doc=None,
    ).problems()
    card = _card(page, LISTED_TARGET)
    assert 'data-status="proved"' in card and "Not claimable" not in card


# --- edge cases (F04-T10 part 2, the node page) -------------------------------------------------


def test_a_reason_carrying_html_is_escaped_on_the_node_page(tmp_path: Path) -> None:
    """A reason explain() has no words for is shown as itself, and escaped (F04-R3)."""
    site, nv = _site_and_node(tmp_path)
    payload = '<script>alert(1)</script>"x'
    page = render.Renderer(
        _with_entry(site, not_claimable=[payload]), repo_url=REPO, decisions_doc=None
    ).node(nv)
    assert "<script>alert" not in page
    assert f"<li>{render.esc(payload)}</li>" in page


def test_an_empty_reasons_list_still_says_not_claimable(tmp_path: Path) -> None:
    """A not-claimable target whose index row names no reason (no curated record, D-6) says so on
    a ready node's page rather than saying nothing."""
    site, nv = _site_and_node(tmp_path)
    page = render.Renderer(
        _with_entry(site, claimable=False, not_claimable=[]), repo_url=REPO, decisions_doc=None
    ).node(nv)
    assert "Not claimable: this target has no curated intake record" in page


def test_a_node_whose_target_has_no_index_row_says_nothing_about_claims(tmp_path: Path) -> None:
    """No index row, no record to state: the page renders and invents no reason."""
    site, nv = _site_and_node(tmp_path)
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(
        dataclasses.replace(nv, target_id="no-such-target")
    )
    assert "Not claimable" not in page
    assert '<h1 class="mono">listed-lemma</h1>' in page


def test_a_proved_node_carries_no_claim_reasons(tmp_path: Path) -> None:
    """F03-Q8: only a ready or speculative node could be claimed, so only its page explains why
    it cannot; a proved node under the same target says nothing about claims."""
    site, nv = _site_and_node(tmp_path)
    proved = dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": "proved"})
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(proved)
    assert "Not claimable" not in page
