"""F22-T16 (ruling 5): a withdrawn explainer chain is one line beneath the live one, never a bare
"every version is withdrawn" above it.

Seen on erdos-1050--h1-v2--h3 (bugs.md P2-5; R1): the proof carries two explainer chains, the
first (``529518ac…``) all withdrawn and the second live. The page printed "Every version of this
explainer is withdrawn" for the first chain directly above the second chain's current explainer,
which reads as a sentence about the whole explainer. The live chains now come first, and a
withdrawn chain is one line naming how many versions it had and who wrote them.
"""

from __future__ import annotations

from pathlib import Path

import gloss_fixture as gf
import pytest
import reading_fixture as rf
import yaml
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
OLD = "## The idea\nAn early reading of the swap.\n"
OLD_REVISED = "## The idea\nAn early reading of the swap, revised.\n"
LIVE = "## The idea\nThe hypothesis already holds both halves; the proof reorders them.\n"
BARE = "Every version of this explainer is withdrawn"


def withdraw(root: Path, record: str, n: int) -> None:
    path = gf.node_dir(root, gf.TUTORIAL) / "withdrawals" / f"2026-10-0{n}T00-00-0{n}Z-carol.yaml"
    path.parent.mkdir(exist_ok=True)
    doc = {
        "schema": "withdrawal/v2",
        "withdraws": record,
        "reason": "Superseded by a clearer account.",
        "author": "carol",
        "date": f"2026-10-0{n}",
    }
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def h3_shape(tmp_path: Path, *, live: bool) -> str:
    """The tutorial's proof with a withdrawn chain of two versions by carol and, when ``live``,
    a second chain by dana that is current."""
    root = rf.chain_tree(tmp_path)
    e1 = gf.explainer(root, gf.TUTORIAL, OLD, author="carol", date="2026-10-01")
    e2 = gf.explainer(
        root, gf.TUTORIAL, OLD_REVISED, author="carol", supersedes=e1, date="2026-10-02"
    )
    withdraw(root, f"explainer/{e1}.md", 3)
    withdraw(root, f"explainer/{e2}.md", 4)
    if live:
        gf.explainer(root, gf.TUTORIAL, LIVE, author="dana", date="2026-10-05")
    rf.write_products(root)
    pages = render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)
    return pages[f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"]


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    return h3_shape(tmp_path_factory.mktemp("h3-shape"), live=True)


def test_the_bare_sentence_is_gone(page: str) -> None:
    assert BARE not in page


def test_the_live_chain_comes_first_and_the_withdrawn_one_is_one_line_below(page: str) -> None:
    live = page.index("the proof reorders them")
    line = page.index("An earlier explainer (2 versions, by carol) was withdrawn")
    assert live < line
    assert "it is in the history below" in page[line : line + 200]
    # The withdrawn words stay on the record, in the history, never as the shown explainer.
    history = page.index('<details class="history"')
    assert history > line
    assert page.index("An early reading of the swap") > history


def test_a_lone_withdrawn_chain_says_so_without_earlier(tmp_path: Path) -> None:
    page = h3_shape(tmp_path, live=False)
    assert BARE not in page
    assert "An explainer (2 versions, by carol) was withdrawn; it is in the history below" in page
