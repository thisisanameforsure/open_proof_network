"""mcpfix WA1 item 6 (testers 2026-11-25, qa-eb L13): after the DCO text changes, every write is
refused ``dco-reaccept-required`` until the identity accepts again, and the MCP had no way to
do that. ``accept_dco`` is ``POST /dco/accept``, one write operation over one route."""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import NODE, McpClient

from opn_api import identity
from opn_api.mcp import auth, bijection, results, surface
from opn_api.mcp.server import BY_NAME, TITLES, TOOLS

DCO = {"dco": {"version": identity.DCO_VERSION, "accepted": True}}


def age(h: Harness, pseudonym: str) -> None:
    held = h.store.get_identity_by_pseudonym(pseudonym)
    assert held is not None
    h.store.set_dco_version(held.id, None)


def test_accept_dco_is_a_bearer_write_over_its_route() -> None:
    tool = BY_NAME["accept_dco"]
    assert tool.write and tool.access == "bearer"
    row = bijection.BY_TOOL["accept_dco"]
    assert row.kind == "write" and row.plain == ("POST /dco/accept",)
    assert row.d28 == "POST /dco/accept (the identity's re-acceptance of the current DCO text)"
    assert TITLES["accept_dco"]
    assert results.load("accept_dco")["title"] == "mcp/accept_dco/v1"
    names = {o["name"] for o in surface.search(TOOLS, TITLES, {})["operations"]}
    assert "accept_dco" in names


def test_the_refusal_names_the_operation(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    age(harness, "alice")
    doc = McpClient(harness).failed("claim_node", {"node_id": NODE}, token=token)
    assert doc["status"] == 403
    assert doc["body"]["error"] == "dco-reaccept-required"
    assert "accept_dco" in doc["body"]["message"]
    assert "POST /dco/accept" in doc["body"]["message"]


def test_accept_dco_lifts_the_refusal(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    age(harness, "alice")
    client = McpClient(harness)
    doc = client.ok("accept_dco", DCO, token=token)
    direct = {
        "identity": {"pseudonym": "alice"},
        "dco": {"version": identity.DCO_VERSION, "accepted": True},
    }
    assert doc == {"status": 200, "body": direct}
    assert results.violations("accept_dco", doc) == []
    held = harness.store.get_identity_by_pseudonym("alice")
    assert held is not None and held.dco_version == identity.DCO_VERSION
    doc = client.ok("claim_node", {"node_id": NODE}, token=token)
    assert doc["status"] == 201


def test_accept_dco_refusals_are_the_routes(harness: Harness) -> None:
    client = McpClient(harness)
    doc = client.failed("accept_dco", DCO)
    assert doc == {"status": auth.UNAUTHORIZED_STATUS, "body": auth.unauthorized(harness.context)}
    token = harness.token_for("code_alice", "alice")
    doc = client.failed(
        "accept_dco", {"dco": {"version": "f7ac75b443f4ca16", "accepted": True}}, token=token
    )
    assert doc["status"] == 400 and doc["body"]["error"] == "dco-version-stale"
    assert results.violations("accept_dco", doc) == []
    doc = client.failed("accept_dco", {}, token=token)
    assert doc["error"] == "arguments-invalid"
