"""F20-T6 / AC9: the two gloss tools in the bijection (F09-R4; D-28 v3.30, D-35 v3.30).

``submit_gloss`` and ``withdraw_gloss`` each map to exactly one route, the route exists in the
routes table, needs a bearer and names D-35's row for it, and the bijection row quotes D-35's
plain-path cell verbatim — so neither tool is an MCP-only capability. The whole table's
completeness is ``test_mcp_surface.py``'s; this file holds the rows F20 added.
"""

from __future__ import annotations

import re

from test_mcp_surface import decisions_text
from test_routes import d35_rows

from opn_api import routes
from opn_api.mcp import bijection
from opn_api.mcp.server import TOOLS

ROWS = {"submit_gloss": "POST /glosses", "withdraw_gloss": "POST /glosses/withdrawals"}


def test_each_gloss_tool_maps_to_its_route() -> None:
    by_label = {r.label: r for r in routes.ROUTES}
    declared = {t.name: t for t in TOOLS}
    for tool, label in ROWS.items():
        assert tool in declared and declared[tool].write
        row = bijection.BY_TOOL[tool]
        assert row.kind == "write" and row.plain == (label,) and row.routes == (label,)
        spec = by_label[label]
        assert spec.write and spec.authenticated and spec.feature == "F20"
        assert spec.d35 == label and label in d35_rows()  # D-35 v3.30 names the endpoint
        assert label in routes.PURPOSES


def test_the_rows_quote_d35_verbatim() -> None:
    d35 = decisions_text('id="d-35"', 'id="d-36"')
    for tool in ROWS:
        assert re.sub(r"\s+", "", bijection.BY_TOOL[tool].d28) in d35, tool


def test_the_table_stays_complete() -> None:
    labels = {r.label for r in routes.ROUTES}
    assert bijection.problems({t.name for t in TOOLS}, labels) == []
