"""F09-T2 / AC8: a source that does not answer is an error result naming it, never partial data."""

from __future__ import annotations

from api_fakes import Harness
from mcp_client import NODE, TARGET, McpClient, seed_node

from opn_api.mcp import results
from opn_api.mcp.server import TOOLS
from opn_gate import schemas


def test_unreachable_source(harness: Harness) -> None:
    """AC8: the fake host raising makes get_target an error result naming the graph, with no
    other field; and the same for every graph-backed read."""
    harness.githost.unreachable = True
    harness.context.files.clear()
    client = McpClient(harness)
    doc = client.failed("get_target", {"target_id": TARGET})
    assert doc["source"] == "graph"
    assert doc["error"] == "graph-unreachable"
    assert set(doc) == {"error", "message", "source"}
    for name, args in (
        ("list_targets", {}),
        ("get_node", {"node_id": NODE}),
        ("get_defs", {"target_id": TARGET}),
        ("get_gate_spec", {"target_id": TARGET}),
        ("get_submission", {"submission_id": "000001"}),
        ("get_schema", {"name": "postmortem/v1"}),
    ):
        failed = client.failed(name, args)
        assert failed["source"] == "graph", name
        assert set(failed) == {"error", "message", "source"}, name
    # A route-backed read names the service, with the status the route answered.
    for name in ("server_info", "list_frontier"):
        failed = client.failed(name)
        assert failed["source"] == "service", name
        assert failed["status"] == 503


def test_partial_bundle_never_served(harness: Harness) -> None:
    """R10: the host failing midway through a bundle (the node's files present, the attempt
    listing failing) is an error result, not a bundle missing its attempts."""
    seed_node(harness)
    client = McpClient(harness)
    whole = client.ok("get_node", {"node_id": NODE})  # the whole bundle, first
    assert whole["context"]["attempts"]["records"]

    original = harness.githost.list_dir

    def failing(repo: str, ref: str, path: str) -> list[str] | None:
        if path.endswith("/attempts"):
            harness.githost.unreachable = True
            try:
                return original(repo, ref, path)
            finally:
                harness.githost.unreachable = False
        return original(repo, ref, path)

    harness.githost.list_dir = failing  # type: ignore[method-assign]
    doc = client.failed("get_node", {"node_id": NODE})
    assert doc["source"] == "graph"
    assert "attempts" not in doc


def test_not_found_names_graph(harness: Harness) -> None:
    """A thing the graph does not have is a not-found error, distinguished from an outage."""
    client = McpClient(harness)
    doc = client.failed("get_target", {"target_id": "ghost"})
    assert doc == {
        "error": "not-found",
        "message": "the graph has no targets/ghost/graph.json at main",
        "source": "graph",
    }
    node = client.failed("get_node", {"node_id": "ghost"})
    assert node["error"] == "node-unknown" and node["source"] == "graph"
    assert client.failed("get_submission", {"submission_id": "999999"})["error"] == "not-found"
    assert client.failed("get_schema", {"name": "mcp/ghost/v1"})["error"] == "not-found"
    assert client.failed("get_schema", {"name": "postmortem/v1"})["error"] == "not-found"


def test_service_refusal_names_service(harness: Harness) -> None:
    """A route-backed read passes the route's refusal through with its status."""
    doc = McpClient(harness).failed("get_precheck", {"job_id": "0" * 26})
    assert doc == {
        "error": "job-unknown",
        "message": "no such precheck job",
        "source": "service",
        "status": 404,
    }


def test_arguments_refused_structured(harness: Harness) -> None:
    """Every refusal of arguments is the schema's error branch, from the adapter."""
    client = McpClient(harness)
    for name, args in (
        ("get_target", {"target_id": "Not Valid"}),
        ("get_node", {}),
        ("get_schema", {"name": "../etc/passwd"}),
        ("get_precheck", {"job_id": "short"}),
        ("list_frontier", {"filters": "origin=authored"}),
        ("claim_node", {"node_id": NODE, "ttl": "5"}),
    ):
        doc = client.failed(name, args)
        assert doc["source"] == "adapter", name
        assert doc["error"] in ("arguments-invalid", "filter-unknown"), name
        assert results.violations(name, doc) == []
    unknown = client.call("no_such_tool", {})
    assert unknown.isError
    assert unknown.structuredContent == {
        "error": "tool-unknown",
        "message": "no such tool no_such_tool",
        "source": "adapter",
    }


def test_get_schema_both_namespaces(harness: Harness) -> None:
    """get_schema serves the graph's protocol schemas and the adapter's result schemas."""
    harness.githost.files["schemas/postmortem/v1.json"] = schemas.schema_path(
        "postmortem/v1"
    ).read_bytes()
    harness.context.files.clear()
    client = McpClient(harness)
    assert client.ok("get_schema", {"name": "postmortem/v1"}) == schemas.load_schema(
        "postmortem/v1"
    )
    for tool in TOOLS:
        assert client.ok("get_schema", {"name": f"mcp/{tool.name}/v1"}) == results.load(tool.name)
