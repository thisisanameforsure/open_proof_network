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


@pytest.mark.xfail(
    strict=True,
    reason=FINDING.format("the target card's status line reads 'listed, listed, not claimable'"),
)
def test_targets_page_does_not_say_listed_twice(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    page = listed[1]["targets/index.html"]
    assert "<dt>Status</dt><dd>listed," in page, "guard: the listed target's status line"
    assert "listed, listed" not in page


@pytest.mark.xfail(
    strict=True,
    reason=FINDING.format(
        "a listed target's node page shows no not-claimable reasons, though targets/index.json "
        "carries them"
    ),
)
def test_node_page_of_a_listed_target_says_why_it_is_not_claimable(
    listed: tuple[list[str], dict[str, str]],
) -> None:
    reasons, pages = listed
    page = pages[NODE_PAGE]
    assert "Not claimable" in page
    for reason in reasons:
        assert render.esc(intake.explain(reason)) in page, reason


@pytest.mark.xfail(
    strict=True,
    reason=FINDING.format(
        "a listed target's frontier row says only 'no' under Claimable, with no reason"
    ),
)
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
