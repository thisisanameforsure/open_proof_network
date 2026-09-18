"""Bench finding: a curated target's page never says in words whether it can be claimed.

A fresh agent read erdos-376's target page and saw only "Status listed, fidelity mechanical-only";
only the frontier table said "Claimable yes". Since F14-R1 a listed target with no drift freeze is
claimable, and F14-R10 wants the target page to tell a reader what they can do with a proof. A
page that speaks only of statuses leaves the reader to know R1 by heart. F04 (R10 of F11,
`why_not_claimable`) already names the reason on the node and frontier pages. The target page
should say it too, in both directions.

Both tests fail today: neither target page contains the word "claim" at all.
"""

from __future__ import annotations

import re
from pathlib import Path

from fixture import (
    COMMIT,
    LISTED_TARGET,
    build_with_evidenced_target,
    build_with_frozen_target,
)

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET_PAGE = f"problems/{LISTED_TARGET}/index.html"


def words(root: Path) -> str:
    """The target page as text: tags stripped, whitespace collapsed."""
    page = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)[TARGET_PAGE]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))


def test_a_claimable_listed_target_page_says_it_is_open_for_claims(tmp_path: Path) -> None:
    """F14-R1: listed and no drift freeze is claimable. F14-R10: the page says what a reader can
    do, and must never say a listed target is not claimable."""
    text = words(build_with_evidenced_target(tmp_path))
    assert re.search(r"(?i)\b(is claimable|open for (claims|work))\b", text), (
        "the target page of a claimable listed target never says it is claimable"
    )
    assert "not claimable" not in text.lower()


def test_a_frozen_target_page_says_it_is_not_claimable_and_why(tmp_path: Path) -> None:
    """F14-R1: an upstream drift freeze (F12-R11) is the one curated not-claimable reason besides
    status. F14-R10 and F11-R10: the reason is named rather than implied."""
    text = words(build_with_frozen_target(tmp_path))
    match = re.search(r"(?i)not claimable", text)
    assert match, "the frozen target's page never says it is not claimable"
    assert re.search(r"(?i)upstream|drift", text[match.start() : match.start() + 300]), (
        "the not-claimable sentence does not name the upstream drift freeze as the reason"
    )
