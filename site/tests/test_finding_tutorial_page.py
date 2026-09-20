"""F04-T23 (agent A, the 2026-09-19 primes run): ``/problems/tutorial/`` said "proved" and "This
problem is open for work" at once, and invited a mathematician to "Become its steward" of a
statement that is off the ledger and that nobody writes up (D-27)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from opn_site import render


def target(*, tutorial: bool, status: str = "resolved") -> Any:
    root = SimpleNamespace(tutorial=tutorial)
    entry = {"root": "r", "status": status, "claimable": True, "not_claimable": []}
    return SimpleNamespace(
        index_entry=entry, nodes={"r": root}, stewards=[], calibration=False, record=None
    )


def renderer() -> Any:
    return SimpleNamespace(
        is_tutorial=render.Renderer.is_tutorial,
        open_count=lambda _tv: 1,
        open_beneath=render.Renderer.open_beneath,
        why_not_claimable=lambda _tv, detail=True: "",
        steward_link=str,
    )


def test_the_tutorial_says_what_it_is_for() -> None:
    html = render.Renderer.target_claimable(renderer(), target(tutorial=True))
    assert "The tutorial." in html and "earn a write token" in html
    assert "open for work" not in html


def test_nobody_is_invited_to_steward_the_tutorial() -> None:
    html = render.Renderer.steward_card(renderer(), target(tutorial=True))
    assert "Become its steward" not in html and "off the ledger and has no steward" in html


def test_an_ordinary_proved_problem_is_unchanged() -> None:
    tv = target(tutorial=False)
    assert "Become its steward" in render.Renderer.steward_card(renderer(), tv)
    assert "The tutorial." not in render.Renderer.target_claimable(renderer(), tv)


def test_a_target_whose_root_the_page_does_not_carry_is_not_the_tutorial() -> None:
    tv = target(tutorial=True)
    tv.nodes = {}
    assert render.Renderer.is_tutorial(tv) is False
