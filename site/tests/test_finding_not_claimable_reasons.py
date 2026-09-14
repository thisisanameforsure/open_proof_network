"""Finding site-not-claimable-reasons (2026-09-13, the Euclid tester): the site says "listed,
listed" and gives the not-claimable reasons on the Targets page only.

The Targets page fills ``$status, $claimable`` with the D-33 status and the words "listed, not
claimable", so a listed target reads "listed, listed, not claimable". The reasons
``targets/index.json`` carries (``not_claimable``) appear in the target card and nowhere a prover
actually lands: the node page and the frontier row of a listed target's node say nothing.

Mike's decision (2026-09-14, plan F04-T10): the target row's claimable word stops repeating the
status; the node page and the frontier row of a node under a not-claimable target carry "Not
claimable" and each reason in ``intake.explain``'s words. Strict xfails until F04-T10 lands
(conventions §2).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from fixture import LISTED_ROOT, LISTED_TARGET, build_with_listed_target

from opn_gate import intake
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE_PAGE = f"nodes/{LISTED_TARGET}/{LISTED_ROOT}/index.html"
FINDING = (
    "finding site-not-claimable-reasons (F04-R5, F04-R7, F11-R10, D-33): {}; "
    "fix: F04-T10 (Mike, 2026-09-14)"
)


@pytest.fixture(scope="module")
def listed(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[str], dict[str, str]]:
    """The not-claimable reasons of the listed target, and the rendered site."""
    from fixture import COMMIT  # noqa: PLC0415

    root = build_with_listed_target(tmp_path_factory.mktemp("listed"))
    site = model.load_site(root, COMMIT)
    reasons = [str(r) for r in site.targets[LISTED_TARGET].index_entry["not_claimable"]]
    assert reasons, "guard: the listed fixture row names reasons"
    return reasons, render.render_site(site, repo_url=REPO)


def test_targets_page_does_not_say_listed_twice(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    page = listed[1]["targets/index.html"]
    assert "<dt>Status</dt><dd>listed," in page, "guard: the listed target's status line"
    assert "listed, listed" not in page


def test_node_page_of_a_listed_target_says_why_it_is_not_claimable(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    reasons, pages = listed
    page = pages[NODE_PAGE]
    assert "Not claimable" in page
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in page, reason


def test_frontier_row_of_a_listed_target_says_why_it_is_not_claimable(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    reasons, pages = listed
    table = pages["frontier/index.html"].split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    rows = [r for r in table.split("</tr>") if NODE_PAGE[:-10] in r]
    assert len(rows) == 1, "guard: the listed node has one frontier row"
    [row] = rows
    assert "Not claimable" in row, row
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in row, reason


# --- edge cases (F04-T10 frontier row) ---------------------------------------------------------


def _row(page: str, node_id: str) -> str:
    table = page.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    [row] = [r for r in table.split("</tr>") if f">{node_id}</a>" in r]
    return row


def _claimable_cell(row: str) -> str:
    """The Claimable cell, found by the header's position (the table's column order is T11's)."""
    keys = [key for key, _label in render.FRONTIER_COLUMNS]
    return row.split("<td>")[1:][keys.index("claimable")].split("</td>", 1)[0]


def test_the_reasons_sit_in_the_claimable_cell_and_add_no_column(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    """Readable at 1200px: the reasons are a sub-line of the Claimable cell, which still starts
    with the entry's own "no" so the column's filter keeps its meaning (R7)."""
    reasons, pages = listed
    page = pages["frontier/index.html"]
    assert page.split("<thead>", 1)[1].count("<th>") == len(render.FRONTIER_COLUMNS) == 17
    cell = _claimable_cell(_row(page, LISTED_ROOT))
    assert cell.startswith("no "), cell
    assert "Not claimable" in cell
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in cell, reason


def test_a_reason_carrying_html_is_escaped_in_the_frontier_row(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    payload = '<script>alert(1)</script>"x'
    entry = {**tv.index_entry, "not_claimable": [payload]}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).frontier()
    row = _row(page, LISTED_ROOT)
    assert "<script>alert" not in page
    assert render.esc(payload) in row


def test_an_empty_reasons_list_still_says_not_claimable_in_the_row(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    entry = {**tv.index_entry, "claimable": False, "not_claimable": []}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).frontier()
    assert "Not claimable: this target has no curated intake record (D-6)" in _row(
        page, LISTED_ROOT
    )


def test_a_claimable_targets_row_carries_no_reasons(tmp_path: Path) -> None:
    site, _nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    entry = {**tv.index_entry, "claimable": True, "not_claimable": []}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    for e in site.frontier["entries"]:
        if e["node_id"] == LISTED_ROOT:
            e["claimable"] = True
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).frontier()
    cell = _claimable_cell(_row(page, LISTED_ROOT))
    assert cell == "yes"


def test_a_blocked_row_under_a_listed_target_carries_no_reasons(tmp_path: Path) -> None:
    """F03-Q8, as on the node page: only a ready or speculative node could be claimed, so a
    blocked row's Status column is its reason and the target's reasons are not repeated."""
    site, nv = _site_and_node(tmp_path)
    nv.graph_entry["status"] = "blocked"
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).frontier()
    row = _row(page, LISTED_ROOT)
    assert _claimable_cell(row) == "no"
    assert "Not claimable" not in row


def test_the_tutorial_row_carries_no_reasons(tmp_path: Path) -> None:
    """D-27: a target without a curated record is claimable exactly when its root is the
    tutorial (F03-Q4), so a tutorial row reads as claimable and explains nothing."""
    site, _nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    entry = {**tv.index_entry, "claimable": True, "not_claimable": []}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    for e in site.frontier["entries"]:
        if e["node_id"] == LISTED_ROOT:
            e["claimable"], e["tutorial"] = True, True
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).frontier()
    row = _row(page, LISTED_ROOT)
    assert "Not claimable" not in row
    cells = row.split("<td>")[1:]
    keys = [key for key, _label in render.FRONTIER_COLUMNS]
    assert cells[keys.index("tutorial")].startswith("yes")


# --- edge cases (F04-T10 part 2) ---------------------------------------------------------------


def _site_and_node(tmp_path: Path) -> tuple[model.Site, model.NodeView]:
    from fixture import COMMIT  # noqa: PLC0415

    site = model.load_site(build_with_listed_target(tmp_path), COMMIT)
    return site, site.targets[LISTED_TARGET].nodes[LISTED_ROOT]


def test_a_reason_carrying_html_is_escaped_on_the_node_page(tmp_path: Path) -> None:
    """A reason explain() has no words for is shown as itself, and escaped (F04-R3)."""
    site, nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    payload = '<script>alert(1)</script>"x'
    entry = {**tv.index_entry, "not_claimable": [payload]}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).node(nv)
    assert "<script>alert" not in page
    assert f"<li>{render.esc(payload)}</li>" in page


def test_an_empty_reasons_list_still_says_not_claimable(tmp_path: Path) -> None:
    """A not-claimable target whose index row names no reason (no curated record, D-6) says so on
    a ready node's page rather than saying nothing."""
    site, nv = _site_and_node(tmp_path)
    tv = site.targets[LISTED_TARGET]
    entry = {**tv.index_entry, "claimable": False, "not_claimable": []}
    targets = {**site.targets, LISTED_TARGET: dataclasses.replace(tv, index_entry=entry)}
    page = render.Renderer(
        dataclasses.replace(site, targets=targets), repo_url=REPO, decisions_doc=None
    ).node(nv)
    assert "Not claimable: this target has no curated intake record" in page


def test_a_node_whose_target_has_no_index_row_says_nothing_about_claims(tmp_path: Path) -> None:
    """No index row, no record to state: the page renders and invents no reason."""
    site, nv = _site_and_node(tmp_path)
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(
        dataclasses.replace(nv, target_id="no-such-target")
    )
    assert "Not claimable" not in page
    assert "<h1>listed-lemma</h1>" in page


def test_a_proved_node_carries_no_claim_reasons(tmp_path: Path) -> None:
    """F03-Q8: only a ready or speculative node could be claimed, so only its page explains why
    it cannot; a proved node under the same target says nothing about claims."""
    site, nv = _site_and_node(tmp_path)
    proved = dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": "proved"})
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(proved)
    assert "Not claimable" not in page
