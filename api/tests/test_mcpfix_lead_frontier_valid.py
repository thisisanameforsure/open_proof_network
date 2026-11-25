"""mcpfix (lead; api-deploy smoke of 946b9a22, 2026-11-25): GET /frontier.json validates as
frontier/v8 while a merge awaits its render.

WB2's overlay put a top-level ``pending_render`` map on the served frontier, after validation and
only while something waited, so the document stopped validating exactly when there was news; the
deploy's smoke caught it live (``Additional properties are not allowed ('pending_render' was
unexpected)``). frontier/v8 is closed and hash-pinned (D-34), so the plain route keeps the valid
half — the waiting entry is not claimable — and the map moves to the MCP's own answer, whose
schema is the adapter's."""

from __future__ import annotations

from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import McpClient
from test_mcpfix_wb2_pending_render import entry, frontier_doc, merged_through_the_route

from opn_gate import schemas


def test_the_served_frontier_validates_while_a_merge_waits(harness: Harness) -> None:
    merged_through_the_route(harness, rendered=False)
    doc = frontier_doc(harness)
    assert entry(doc, TUTORIAL_NODE)["claimable"] is False
    assert schemas.violations(doc) == []
    assert "pending_render" not in doc


def test_the_mcp_answer_names_what_waits(harness: Harness) -> None:
    merged_at = merged_through_the_route(harness, rendered=False)
    out = McpClient(harness).ok("list_frontier", {"target_id": "propositional"})
    assert out["pending_render"] == {
        TUTORIAL_NODE: {"pr": 7, "kind": "proof", "merged_at": merged_at}
    }
    full = McpClient(harness).ok("list_frontier", {"full": True})
    assert "pending_render" not in full  # full is GET /frontier.json exactly
