"""F04-T22 (decisions v3.20, D-33): a proved problem with open statements beneath it says so.

The 2026-09-19 primes run: ``/problems/euclid-primes/`` said "Proved: its statement no longer
accepts work" above three open variants, and each variant's page said "Not claimable, because:
the target's D-33 status is resolved", while the service accepted proofs of all of them. The page
now follows the gate's own rule (``products.open_beneath``), so it cannot disagree with the
frontier.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from opn_site import render


def target(reasons: list[str], *, claimable: bool = False, status: str = "resolved") -> Any:
    entry = {"claimable": claimable, "status": status, "not_claimable": reasons, "root": "r"}
    return SimpleNamespace(index_entry=entry, nodes={"r": SimpleNamespace(tutorial=False)})


def renderer(open_count: int, tv: Any = None) -> Any:
    """Just enough of the renderer for the two sentences under test."""
    stub = SimpleNamespace(
        open_count=lambda _tv: open_count,
        open_beneath=render.Renderer.open_beneath,
        is_tutorial=render.Renderer.is_tutorial,
        why_not_claimable=lambda _tv, detail=True: "<p>Not claimable, because:</p>",
        site=SimpleNamespace(targets={"t": tv}),
    )
    return stub


@pytest.mark.parametrize(("count", "words"), [(1, "1 statement"), (3, "3 statements")])
def test_a_proved_problem_names_the_open_statements_beneath_it(count: int, words: str) -> None:
    tv = target(["status-resolved"])
    html = render.Renderer.target_claimable(renderer(count), tv)
    assert "own statement is closed" in html and words in html and "open for work" in html
    assert "no longer accepts work" not in html


def test_a_proved_problem_with_nothing_beneath_it_is_closed_as_before() -> None:
    html = render.Renderer.target_claimable(renderer(0), target(["status-resolved"]))
    assert "no longer accepts work" in html


def test_a_second_reason_still_closes_the_page() -> None:
    tv = target(["status-resolved", "upstream-drift"])
    html = render.Renderer.target_claimable(renderer(2), tv)
    assert "no longer accepts work" in html


def test_a_variant_under_a_resolved_root_is_not_told_it_is_unclaimable() -> None:
    nv: Any = SimpleNamespace(target_id="t", status="ready")
    open_tv, closed_tv = target(["status-resolved"]), target(["no-steward"], status="listed")
    assert render.Renderer.node_not_claimable(renderer(1, open_tv), nv) == ""
    assert "Not claimable" in render.Renderer.node_not_claimable(renderer(1, closed_tv), nv)
