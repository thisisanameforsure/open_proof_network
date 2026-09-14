"""F09-T7: pending submissions through the MCP adapter — driven through the routes that record
today (``POST /annexes``), since ``POST /submissions``' record call waits on another session's
commit (``test_finding_pending_submissions.py`` holds those as strict xfails).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import NODE, McpClient, seed_node

from opn_api.mcp import reads
from opn_api.mcp.calls import Call

FAILED_GATE = {"name": "gate", "status": "completed", "conclusion": "failure", "url": "u"}


def annex(h: Harness, token: str, node: str = TUTORIAL_NODE) -> dict[str, Any]:
    r = h.client.post(
        "/annexes", json={"node_id": node, "text": "An informal argument.\n"}, headers=h.auth(token)
    )
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def test_get_submission_tool_is_the_route_for_an_open_append(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    harness.githost.set_pull_request_state(1, mergeable_state="blocked", runs=[FAILED_GATE])
    over_http = harness.client.get("/submissions/1").json()
    assert over_http["pull_request"]["runs"] == [FAILED_GATE]
    client = McpClient(harness)
    assert client.ok("get_submission", {"submission_id": "1"}) == over_http
    assert client.ok("get_submission", {"submission_id": "000001"}) == over_http


def test_get_node_carries_only_its_own_open_submissions_and_drops_the_merged(
    harness: Harness,
) -> None:
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    opened = annex(harness, token, node=NODE)
    annex(harness, token, node=TUTORIAL_NODE)
    client = McpClient(harness)
    [entry] = client.ok("get_node", {"node_id": NODE})["submissions"]["open"]
    assert (entry["pr_number"], entry["id"], entry["node_id"]) == (1, opened["id"], NODE)
    assert entry == harness.client.get("/submissions/1").json()["submission"]

    harness.githost.set_pull_request_state(1, state="closed", merged=True)
    # The read above cached the open state for the window; age it, as a watcher would wait.
    window = harness.settings.frontier_max_stale_s
    for cached in harness.context.pulls.values():
        cached.fetched_at = time.monotonic() - (window + 1)
    assert harness.client.get("/submissions/1").json()["submission"]["closed"] is not None
    assert client.ok("get_node", {"node_id": NODE})["submissions"] == {"open": []}


def test_list_submissions_handler_is_the_snapshot(harness: Harness) -> None:
    """Built, not registered until D-28 has its row: the handler over the live application is
    ``GET /submissions.json`` exactly."""
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)

    async def go() -> dict[str, Any]:
        transport = httpx.ASGITransport(app=harness.app)
        async with httpx.AsyncClient(
            transport=transport, base_url=harness.settings.public_url
        ) as http:
            return await reads.list_submissions(Call(ctx=harness.context, http=http), {})

    over_tool = asyncio.run(go())
    assert over_tool == harness.client.get("/submissions.json").json()
    assert [e["pr_number"] for e in over_tool["open"]] == [1]
