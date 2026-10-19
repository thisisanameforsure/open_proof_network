"""F09-T74 (D-25, D-28 v3.45): the read tools' words say what the literature fields now carry.

``get_node`` says the bundle inlines each literature record's summary and references and that a
confirmed status may carry ``disputes``; ``list_frontier`` says an entry's ``literature`` may carry
``disputes``. A clause each, never a paragraph: ``tools/list`` is a context cost the owner's review
of 2026-10-06 measured, and ``test_finding_mcp_context_budget`` holds the whole listing to its pin.
"""

from __future__ import annotations

from opn_api.mcp.server import TOOLS

BY_NAME = {t.name: t for t in TOOLS}


def test_get_node_says_the_bundle_inlines_the_records_and_may_carry_disputes() -> None:
    node = BY_NAME["get_node"].description
    assert "`literature`" in node and "`literature_proposed`" in node
    assert "summary" in node and "references" in node and "`disputes`" in node


def test_list_frontier_says_an_entry_may_carry_disputes() -> None:
    frontier = BY_NAME["list_frontier"].description
    assert "`literature`" in frontier and "`literature_proposed`" in frontier
    assert "`disputes`" in frontier
