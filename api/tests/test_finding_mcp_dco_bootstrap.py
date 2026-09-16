"""Finding: an MCP-only client could not mint a token — the DCO version was HTTP-only.

Found 2026-09-16 by the Erdős 412 live run, which had to step outside MCP for exactly one call.

F09-T6 closed the first half of this (``get_token`` is a tool, and an anonymous tutorial precheck
passes through), so the refusal already told a caller how to bootstrap. But ``POST /tokens``
requires ``dco: {version, accepted: true}`` and refuses a wrong version with
``dco-version-stale``; the version was published *only* by ``GET /dco.json``. There was no
``get_dco`` tool, ``server_info`` carries no dco key (``info.json`` is the graph's product), and
``get_schema`` serves schemas, not documents. So the client the guide itself recommends —
``claude mcp add --transport http`` — was read-only for ever.

This was the bijection rule (D-28) failing in the direction nothing checked.
``bijection.problems`` tests tool → row and row → route; it has no opinion about a *route* with no
tool, and ``GET /dco.json`` was one. The rule's own words are "every MCP operation is exactly
reproducible with plain git and HTTP", which that satisfied — what was broken is the converse, on
the one path every new identity must walk.

Fixed 2026-09-16 on the owner's call: a D-28 notation note admits ``get_dco()`` to the read table
(the same editorial form as 2026-09-14's ``get_token`` and ``propose_witness``, no
``PROTOCOL_VERSION`` bump), and the tool, its bijection row and its result schema followed. Held
as strict expected failures until then.
"""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import McpClient

BAD_VERSION = "0" * 16


def test_a_get_dco_tool_publishes_the_version_a_token_needs(harness: Harness) -> None:
    """The tool is ``GET /dco.json``, body for body: the DCO's version and its text."""
    client = McpClient(harness)
    names = {t.name for t in client.list_tools()}
    assert "get_dco" in names, sorted(names)

    doc = client.ok("get_dco")
    over_http = harness.client.get("/dco.json")
    assert over_http.status_code == 200, over_http.text
    assert doc == over_http.json()
    assert isinstance(doc["version"], str) and doc["version"]
    assert "Developer Certificate of Origin" in doc["text"]


def test_the_version_the_tool_publishes_is_the_one_tokens_accepts(harness: Harness) -> None:
    """The property that matters, stated once: the value ``get_token`` demands is reachable
    through a tool, and it is the *right* value.

    Asserted where it is enforced rather than by equality with a constant — a token request
    carrying the tool's version is never refused for its version, and one carrying any other
    version is. This is the assertion to keep if the fix ever takes another shape than a
    ``get_dco`` tool.
    """
    client = McpClient(harness)
    published = client.ok("get_dco")["version"]

    refusals = {}
    for label, version in (("published", published), ("wrong", BAD_VERSION)):
        r = harness.client.post(
            "/tokens",
            json={
                "proof": {"kind": "tutorial", "job_id": "01M00000000000000000000000", "nonce": "x"},
                "pseudonym": f"dco-{label}",
                "dco": {"version": version, "accepted": True},
            },
        )
        refusals[label] = (r.json() or {}).get("error")

    assert refusals["wrong"] == "dco-version-stale", refusals
    assert refusals["published"] != "dco-version-stale", (
        f"the version get_dco publishes ({published!r}) is not the one POST /tokens accepts; "
        f"an MCP-only client would be refused: {refusals}"
    )
