"""Finding: an MCP-only client still cannot mint a token — the DCO version is HTTP-only.

Found 2026-09-16 by the Erdős 412 live run, which had to step outside MCP for exactly one call.

F09-T6 closed the first half of this (``get_token`` is a tool, and an anonymous tutorial
precheck passes through), so the refusal now tells a caller how to bootstrap. But ``POST
/tokens`` requires ``dco: {version, accepted: true}`` and refuses a wrong version with
``dco-version-stale``; the version is published *only* by ``GET /dco.json``. There is no
``get_dco`` tool, ``server_info`` carries no dco key (``info.json`` is the graph's product:
``protocol_version``, ``rate_limit_policy``, ``rendered_from``, ``schema``, ``schemas``,
``targets``), and ``get_schema`` serves schemas, not documents. So the client the guide itself
recommends — ``claude mcp add --transport http`` — is read-only for ever.

This is the bijection rule (D-28) failing in the direction nothing checks. ``bijection.problems``
tests tool → row and row → route; it has no opinion about a *route* with no tool, and
``GET /dco.json`` is one. The rule's own words are "every MCP operation is exactly reproducible
with plain git and HTTP", which this satisfies — and the thing that is broken is the converse,
on the one path every new identity must walk.

**Both tests are strict xfails, because the fix is not this session's to make.** A ``get_dco``
row must quote D-28's or D-35's own cell verbatim (``test_d28_rows_verbatim``), and ``/dco.json``
appears nowhere in the decisions document — so the fix is a D-28 notation note of the kind
2026-09-14 added for ``get_token`` and ``propose_witness``, and a decision changes only through
the architecture document's own process (constitution; the build log's rule of 2026-09-07).
Recorded red so it cannot be forgotten, and so the task that takes it flips these to green.
"""

from __future__ import annotations

import pytest
from api_fakes import Harness
from mcp_client import McpClient

FIX = (
    "fix: a D-28 notation note admitting GET /dco.json, then a get_dco read tool with its "
    "bijection row and result schema (owner's call, 2026-09-16)"
)


@pytest.mark.xfail(strict=True, reason=f"finding mcp-dco-bootstrap (D-28, D-23); {FIX}")
def test_a_get_dco_tool_publishes_the_version_a_token_needs(harness: Harness) -> None:
    """The missing tool: the DCO's version and text, as ``GET /dco.json`` serves them."""
    client = McpClient(harness)
    names = {t.name for t in client.list_tools()}
    assert "get_dco" in names, sorted(names)

    doc = client.ok("get_dco")
    over_http = harness.client.get("/dco.json")
    assert over_http.status_code == 200, over_http.text
    assert doc == over_http.json()
    assert isinstance(doc["version"], str) and doc["version"]


@pytest.mark.xfail(strict=True, reason=f"finding mcp-dco-bootstrap (D-28, D-23); {FIX}")
def test_the_whole_bootstrap_is_reachable_without_plain_http(harness: Harness) -> None:
    """The property that matters, stated once: every value ``get_token`` demands can be read
    through a tool. Today ``dco.version`` cannot, so an MCP-only client is read-only for ever.

    This is the assertion to keep if the fix takes another shape than a ``get_dco`` tool.
    """
    client = McpClient(harness)
    tools = {t.name for t in client.list_tools()}
    reachable: set[str] = set()
    for name in tools:
        if name == "get_dco":
            reachable.add("dco.version")
    assert "dco.version" in reachable, (
        "no tool publishes the DCO version that POST /tokens requires; an MCP-only client "
        "cannot mint an identity"
    )
