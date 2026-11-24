"""F09-T78 (D-28 v3.50): the MCP surface is three tools — search, read, write — over the catalog
of operations, with the 42 named tools kept at ``/mcp?surface=v1`` for a transition window.

Every operation is still exactly one endpoint or graph path (the bijection is per operation);
``write`` is where every state-changing operation lives and refuses without a bearer, except the
writes anonymous by design (``get_token`` mints the identity; ``precheck_submission`` and
``check_lean`` let their endpoint decide)."""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import LEGACY_PATH, NODE, McpClient, seed_node
from test_mcp_auth import ANONYMOUS_WRITES, MINIMAL

from opn_api.mcp import auth, bijection
from opn_api.mcp.server import TOOLS

SURFACE = {"search", "read", "write"}
#: The new surface's tools/list, compact JSON, must stay under this: the point of the change.
LIST_BUDGET = 8_000


def listed(client: McpClient) -> dict[str, Any]:
    return {t.name: t for t in client.list_tools()}


def test_three_tools_at_mcp(harness: Harness) -> None:
    """R11: /mcp lists exactly search, read and write; reads are annotated read-only and the
    write tool is not; the whole list is a small fraction of the 42 tools it replaces."""
    tools = listed(McpClient(harness, raw=True))
    assert set(tools) == SURFACE
    assert tools["search"].annotations.readOnlyHint is True
    assert tools["read"].annotations.readOnlyHint is True
    assert tools["write"].annotations.readOnlyHint is False
    size = len(json.dumps([t.model_dump(mode="json", exclude_none=True) for t in tools.values()]))
    assert size < LIST_BUDGET, size


def test_legacy_surface_behind_the_flag(harness: Harness) -> None:
    """R12: /mcp?surface=v1 serves the named tools exactly as before."""
    legacy = McpClient(harness, path=LEGACY_PATH)
    assert set(listed(legacy)) == {t.name for t in TOOLS}
    assert legacy.ok("server_info")["protocol_version"]


def test_search_catalog_is_the_bijection_table(harness: Harness) -> None:
    """R11: search with no query lists every operation once, with its kind and plain path from
    the bijection table, so a tool without a plain path still cannot ship."""
    doc = McpClient(harness, raw=True).ok("search", {})
    ops = {o["name"]: o for o in doc["operations"]}
    assert set(ops) == {t.name for t in TOOLS}
    for tool in TOOLS:
        row = bijection.BY_TOOL[tool.name]
        assert ops[tool.name]["kind"] == row.kind
        assert ops[tool.name]["plain"] == row.d28
        assert ops[tool.name]["auth"] == tool.access


def test_search_by_query_ranks_and_carries_schemas(harness: Harness) -> None:
    """R11: a query returns the matching operations best first, each with its input schema and
    description, so an agent goes from search straight to read or write."""
    client = McpClient(harness, raw=True)
    doc = client.ok("search", {"query": "claim a node"})
    first = doc["operations"][0]
    assert first["name"] == "claim_node"
    assert first["input_schema"]["required"] == ["node_id"]
    assert first["description"]
    # An exact operation name is always first.
    assert client.ok("search", {"query": "get_node"})["operations"][0]["name"] == "get_node"
    # Named operations come back in full, output schema included on request.
    named = client.ok("search", {"operations": ["get_node"], "include_output_schema": True})
    [op] = named["operations"]
    assert op["name"] == "get_node"
    assert "output_schema" in op


def test_search_unknown_name(harness: Harness) -> None:
    doc = McpClient(harness, raw=True).failed("search", {"operations": ["no_such_op"]})
    assert doc["error"] == "operation-unknown"


def test_read_equals_the_named_tool(harness: Harness) -> None:
    """R11: read(operation, arguments) answers byte for byte as the named tool did."""
    seed_node(harness)
    new, legacy = McpClient(harness, raw=True), McpClient(harness, path=LEGACY_PATH)
    for name, args in (
        ("server_info", {}),
        ("list_targets", {}),
        ("list_frontier", {}),
        ("get_node", {"node_id": NODE}),
    ):
        got = new.ok("read", {"operation": name, "arguments": args})
        assert got == legacy.ok(name, args), name


def test_read_refuses_a_write_and_write_refuses_a_read(harness: Harness) -> None:
    """R11: the kind is the tool's, so a harness rule that allows read and asks on write means
    what it says."""
    client = McpClient(harness, raw=True)
    doc = client.failed("read", {"operation": "claim_node", "arguments": {"node_id": NODE}})
    assert doc["error"] == "operation-kind-mismatch"
    assert "write" in doc["message"]
    doc = client.failed("write", {"operation": "list_targets", "arguments": {}})
    assert doc["error"] == "operation-kind-mismatch"
    assert harness.store.list_claims() == []


def test_unknown_operation_names_search(harness: Harness) -> None:
    doc = McpClient(harness, raw=True).failed("read", {"operation": "nope", "arguments": {}})
    assert doc["error"] == "operation-unknown"
    assert "search" in doc["message"]


def test_write_needs_a_bearer(harness: Harness) -> None:
    """R2 through write (R11): every bearer write without a token is the unauthorized envelope and
    reaches no endpoint; the anonymous-by-design writes reach their endpoint."""
    client = McpClient(harness, raw=True)
    body = auth.unauthorized(harness.context)
    for tool in TOOLS:
        if not tool.write or tool.name in ANONYMOUS_WRITES:
            continue
        doc = client.failed("write", {"operation": tool.name, "arguments": MINIMAL[tool.name]})
        assert doc == {"status": auth.UNAUTHORIZED_STATUS, "body": body}, tool.name
    assert harness.store.list_claims() == []
    assert harness.githost.pushes == []
    for name in sorted(ANONYMOUS_WRITES):
        doc = client.failed("write", {"operation": name, "arguments": MINIMAL[name]})
        assert doc["status"] == 400, (name, doc)


def test_write_with_a_bearer_reaches_the_endpoint(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    doc = McpClient(harness, raw=True).ok(
        "write", {"operation": "claim_node", "arguments": {"node_id": NODE, "ttl": 5}}, token=token
    )
    assert doc["status"] == 201
    assert doc["body"]["pseudonym"] == "alice-p"


def test_read_of_own_records_needs_a_bearer(harness: Harness) -> None:
    """A read declared ``bearer`` (the caller's own records) is refused through read without
    one, as the named tool was."""
    doc = McpClient(harness, raw=True).failed(
        "read", {"operation": "list_my_claims", "arguments": {}}
    )
    assert doc["status"] == auth.UNAUTHORIZED_STATUS


def test_operation_arguments_are_validated(harness: Harness) -> None:
    """The operation's own input schema is applied, and the refusal names the argument."""
    doc = McpClient(harness, raw=True).failed("read", {"operation": "get_node", "arguments": {}})
    assert doc["error"] == "arguments-invalid"
    assert "node_id" in doc["message"]


def test_instructions_teach_the_three_tools(harness: Harness) -> None:
    text = McpClient(harness, raw=True).initialize().instructions or ""
    for word in ("search", "read", "write", "surface=v1"):
        assert word in text, word
