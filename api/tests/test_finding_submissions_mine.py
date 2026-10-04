"""F07-T70, F09-T17 (audit 2026-10-04; the owner approved both surfaces): an agent's own
submissions and its own fast-check records, by token.

The story. An agent that lost the receipt of a pull request it opened (a restarted session, a
context window that dropped it) could find it again only by reading every open pull request on the
graph (``GET /submissions.json``) and matching its pseudonym, and could not find one that had
already merged or closed at all. ``GET /claims/mine`` (F05-T14) solved the same problem for claims;
``GET /submissions/mine`` is its twin: the caller's open records, each with its place in its lane
of the queue, and its most recent finished ones, with how each ended. The MCP adapter gains
``get_my_submissions`` for it and ``get_check`` for ``GET /checks/{id}``, the caller's own record
of one fast check, which had no tool (D-28: no MCP-only capability, and no HTTP-only one either).
Both are reads that need the caller's bearer, because what they read is the caller's own.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_finding_queue_position import cold, listing
from test_pending_submissions import MERGE_SHA, annex, get
from test_store_seam import dynamo

from opn_api import routes
from opn_api.store import CheckLog, MemoryStore


@pytest.fixture(params=["memory", "dynamodb"])
def h(request: pytest.FixtureRequest) -> Iterator[Harness]:
    store = MemoryStore() if request.param == "memory" else dynamo()
    harness = make_harness(store=store)
    with harness.client:
        yield harness


def mine(h: Harness, token: str | None) -> Any:
    return h.client.get("/submissions/mine", headers=h.auth(token) if token else {})


def mine_doc(h: Harness, token: str) -> dict[str, Any]:
    r = mine(h, token)
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


# --- GET /submissions/mine ------------------------------------------------------------------------


def test_mine_lists_the_callers_open_submissions_and_nobody_elses(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    first = annex(h, alice)
    theirs = annex(h, bob)
    second = annex(h, alice)
    doc = mine_doc(h, alice)
    assert doc["pseudonym"] == "alice-p"
    assert [e["id"] for e in doc["open"]] == [first["id"], second["id"]]
    assert doc["recent"] == []
    # each open entry is the listing's own entry: the record and its place in the queue
    listed = {e["id"]: e for e in listing(h)["open"]}
    assert doc["open"] == [listed[first["id"]], listed[second["id"]]]
    assert [e["id"] for e in mine_doc(h, bob)["open"]] == [theirs["id"]]
    assert all(e["pseudonym"] == "alice-p" for e in doc["open"])


def test_a_finished_submission_moves_to_recent_with_how_it_ended(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    merged = annex(h, alice)  # #1
    closed = annex(h, alice)  # #2
    still_open = annex(h, alice)  # #3
    annex(h, bob)  # #4, finished too, and never alice's
    h.githost.set_pull_request_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA)
    h.githost.set_pull_request_state(2, state="closed")
    h.githost.set_pull_request_state(4, state="closed")
    cold(h)  # nothing cached: each read below is the live one that finds it finished
    for number in ("1", "2", "4"):
        get(h, number)
    doc = mine_doc(h, alice)
    assert [e["id"] for e in doc["open"]] == [still_open["id"]]
    # newest first
    assert [(e["id"], e["state"]) for e in doc["recent"]] == [
        (closed["id"], "closed"),
        (merged["id"], "merged"),
    ]
    assert all(e["closed"] is not None for e in doc["recent"])
    assert mine_doc(h, bob)["recent"][0]["pr_number"] == 4


def test_recent_is_capped_newest_first() -> None:
    from opn_api import pending  # noqa: PLC0415

    h = make_harness({"OPN_API_OPEN_PRS_PER_IDENTITY": "50"})
    alice = h.token_for("code_alice", "alice-p")
    total = pending.MAX_RECENT_MINE + 2
    for _ in range(total):
        annex(h, alice)
    for number in range(1, total + 1):
        h.githost.set_pull_request_state(number, state="closed")
    cold(h)
    for number in range(1, total + 1):
        get(h, str(number))
    recent = mine_doc(h, alice)["recent"]
    assert [e["pr_number"] for e in recent] == list(
        range(total, total - pending.MAX_RECENT_MINE, -1)
    )


def test_mine_without_a_bearer_is_401() -> None:
    h = make_harness()
    r = mine(h, None)
    assert r.status_code == 401, r.text
    assert r.json()["error"] == "unauthenticated"
    assert mine(h, "not-a-token").status_code == 401


def test_the_route_is_in_the_table_as_an_authenticated_read() -> None:
    spec = next((r for r in routes.ROUTES if r.label == "GET /submissions/mine"), None)
    assert spec is not None, "GET /submissions/mine is not in the routes table"
    assert spec.authenticated and not spec.write and spec.d35 is None
    # it is matched before /submissions/{submission_id}, which would refuse "mine" as an id
    labels = [r.label for r in routes.ROUTES]
    assert labels.index("GET /submissions/mine") < labels.index("GET /submissions/{submission_id}")


# --- MCP ------------------------------------------------------------------------------------------


def test_get_my_submissions_over_mcp_equals_the_route() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    annex(h, alice)
    over_mcp = McpClient(h).call("get_my_submissions", {}, token=alice)
    assert not over_mcp.isError, over_mcp.structuredContent
    assert over_mcp.structuredContent == mine_doc(h, alice)


def test_get_my_submissions_without_a_token_is_refused_before_the_route() -> None:
    result = McpClient(make_harness()).call("get_my_submissions", {})
    assert result.isError
    doc = result.structuredContent or {}
    assert doc.get("error") == "unauthenticated" and doc.get("status") == 401, doc


def check_record(identity_id: str, check_id: str = "01M0000000000000000000CHK1") -> CheckLog:
    return CheckLog(
        id=check_id,
        created="2026-10-04T12:00:00Z",
        caller_kind="identity",
        caller=identity_id,
        target_id="propositional",
        node_id=None,
        mode="check",
        environment="lean-4.33.1",
        content_sha256="0" * 64,
        content_bytes=10,
        outcome="answered",
        okay=True,
        error_count=0,
        lint=[],
        axle_request_id=None,
        upstream_status=200,
        latency_ms=5,
    )


def test_get_check_over_mcp_is_the_owners_record_and_nobody_elses() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    who = h.store.get_identity_by_pseudonym("alice-p")
    assert who is not None
    record = check_record(who.id)
    h.store.put_check(record)
    client = McpClient(h)
    over_mcp = client.call("get_check", {"check_id": record.id}, token=alice)
    assert not over_mcp.isError, over_mcp.structuredContent
    plain = h.client.get(f"/checks/{record.id}", headers=h.auth(alice))
    assert plain.status_code == 200, plain.text
    assert over_mcp.structuredContent == plain.json()
    # another identity: the route's own not-found, passed through
    theirs = client.failed("get_check", {"check_id": record.id}, token=bob)
    assert (theirs.get("error"), theirs.get("status")) == ("check-unknown", 404), theirs
    # no token: refused before the route
    anon = client.failed("get_check", {"check_id": record.id})
    assert (anon.get("error"), anon.get("status")) == ("unauthenticated", 401), anon


def test_the_tools_are_reads_that_need_the_callers_bearer() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    for name in ("get_my_submissions", "get_check"):
        tool = BY_NAME.get(name)
        assert tool is not None, f"{name} is not declared"
        assert not tool.write and tool.needs_bearer, name
