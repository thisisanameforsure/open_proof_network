"""F05-T23, F09-T15: the error-code catalog is served (audit 2026-10-04; owner-approved surface).

``opn_gate.codes`` (F13-T29) says, for every code the gate and the service emit, what it means
and what to do. An agent meets a code in a verdict, a response body or an MCP error result, so
the catalog is served where it is already looking: ``GET /errors.json``, an open read with no
D-35 row like ``/hosted-checkers.json``, and the MCP read ``list_error_codes``, which is that
route body for body (D-28: no MCP-only capability). Both take an optional code prefix.
"""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import McpClient

from opn_api import routes
from opn_api.mcp import bijection, results
from opn_gate import codes

PATH = "/errors.json"
LABEL = f"GET {PATH}"
TOOL = "list_error_codes"


def test_the_route_is_an_open_read_with_no_d35_row() -> None:
    (spec,) = [r for r in routes.ROUTES if r.label == LABEL]
    assert not spec.authenticated and not spec.write and spec.d35 is None
    assert LABEL in routes.PURPOSES


def test_the_route_serves_the_whole_catalog_without_a_token(harness: Harness) -> None:
    r = harness.client.get(PATH)
    assert r.status_code == 200, r.text
    assert r.json() == codes.document()
    assert r.json()["count"] == len(codes.CATALOG)
    assert "public" in r.headers.get("cache-control", ""), r.headers
    assert r.headers["content-type"].startswith("application/json")


def test_the_route_filters_by_prefix(harness: Harness) -> None:
    r = harness.client.get(PATH, params={"prefix": "witness-"})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc == codes.document("witness-")
    assert doc["codes"] and all(c["code"].startswith("witness-") for c in doc["codes"])
    assert harness.client.get(PATH, params={"prefix": "zz-"}).json()["codes"] == []


def test_every_code_a_response_carries_is_in_the_catalog(harness: Harness) -> None:
    """The point of the route: a refusal's own code is looked up in it and has a remedy."""
    refusal = harness.client.post("/claims", json={})  # no bearer
    assert refusal.status_code == 401
    by_code = {c["code"]: c for c in harness.client.get(PATH).json()["codes"]}
    assert by_code[refusal.json()["error"]]["remedy"]
    assert by_code["not-found"]["remedy"]


def test_the_tool_is_the_route_body_for_body(harness: Harness) -> None:
    client = McpClient(harness)
    tools = {t.name: t for t in client.list_tools()}
    assert TOOL in tools
    annotations = tools[TOOL].annotations
    assert annotations is not None and annotations.readOnlyHint
    doc = client.ok(TOOL)
    assert doc == harness.client.get(PATH).json()
    assert results.violations(TOOL, doc) == []
    narrowed = client.ok(TOOL, {"prefix": "relation-"})
    assert narrowed == harness.client.get(PATH, params={"prefix": "relation-"}).json()
    assert narrowed["codes"] and narrowed["prefix"] == "relation-"


def test_the_tool_needs_no_token_and_maps_to_the_route() -> None:
    row = bijection.BY_TOOL[TOOL]
    assert row.kind == "read" and row.plain == (LABEL,)
