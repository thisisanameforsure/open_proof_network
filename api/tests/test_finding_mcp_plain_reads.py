"""Finding mcp-plain-reads (agent C, the 2026-09-19 primes run): the guide says "there is no
MCP-only capability", and the converse was false for two plain reads with no tool — ``GET /``,
the service's own route index, and ``GET /hosted-checkers.json``. An MCP-only agent could not
see the plain path behind a tool, nor which targets ``check_lean`` can serve. The owner asked for
both (2026-09-20); D-28's read table admits them by notation note (F09-T9).
"""

from __future__ import annotations

import pytest
from api_fakes import Harness
from mcp_client import McpClient

from opn_api.mcp import results


@pytest.mark.parametrize(
    ("tool", "path"),
    [("list_routes", "/"), ("get_hosted_checkers", "/hosted-checkers.json")],
)
def test_the_tool_is_its_plain_route_body_for_body(harness: Harness, tool: str, path: str) -> None:
    client = McpClient(harness)
    assert tool in {t.name for t in client.list_tools()}
    doc = client.ok(tool)
    over_http = harness.client.get(path)
    assert over_http.status_code == 200, over_http.text
    assert doc == over_http.json()
    assert results.violations(tool, doc) == []


def test_every_tool_has_a_plain_route_in_the_index_it_now_serves(harness: Harness) -> None:
    """The point of ``list_routes``: the index an MCP-only agent reads names the two routes
    themselves, so the bijection is visible from inside the adapter."""
    routes = {(r["method"], r["path"]) for r in McpClient(harness).ok("list_routes")["routes"]}
    assert ("GET", "/") in routes and ("GET", "/hosted-checkers.json") in routes
