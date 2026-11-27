"""F34-T30 (REMINDERS-erdos-257 item 4; handoff §2 principle 2, mockup ``New-Erdos257``): rust
means *refuted* only. The route selector's edges are grey hairlines (the mockup's rule colour)
whatever side they lead to; only the numbered ends of routes that would disprove the problem are
rust, and a chosen end is filled in the selection's own colour (F30-T10).
"""

from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css").read_text(
    encoding="utf-8"
)


def rules() -> list[tuple[str, str]]:
    """Every rule of the stylesheet, as (selector, body)."""
    return [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS)]


def test_no_selector_edge_is_rust() -> None:
    rust = [
        s
        for s, b in rules()
        if "sel-edge" in s
        and not re.search(
            r"\.sel-edge\[aria-pressed|\.sel-edge\[data-view\]:hover|previewed|focus", s
        )
        and "var(--refute)" in b
    ]
    assert rust == [], rust


def test_an_edge_is_an_ink_hairline() -> None:
    base = [b for s, b in rules() if s == ".selector .sel-edge"]
    assert base, "the edge rule"
    # the mockup draws them as the rule colour (README: "ink hairlines"; the screenshot is grey)
    assert "stroke: var(--rule-strong)" in base[-1] and "stroke-width: 1;" in base[-1], base[-1]


def test_only_a_disproving_end_is_rust() -> None:
    rust = [s for s, b in rules() if s.startswith(".selector") and "var(--refute)" in b]
    assert rust, "the disproving ends are coloured"
    for s in rust:
        for part in s.split(","):
            assert ".kind-leaf.side-refutes" in part, part
    # a chosen end is filled by the one pressed rule (F30-T10's selection colour), which comes
    # after the rust rule and so wins over it
    pressed = '.selector .sel-node[aria-pressed="true"] .dot'
    assert CSS.index(pressed) > CSS.index(".selector .kind-leaf.side-refutes .dot")
