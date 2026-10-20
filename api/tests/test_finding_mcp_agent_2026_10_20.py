"""F09-T75 (an agent's report, 2026-10-20): three things the MCP surface did not say or did wrong.

1. ``get_my_submissions`` failed its own output validation once the caller had a finished
   submission: every ``recent`` entry is the record as the routes serve it, which carries
   ``automation`` (F25-R2), and the result schema's ``finished`` entry did not allow it.
2. ``get_submission`` takes ``submission_id`` (D-28 names it so), while the listings and every
   append receipt name the same value ``id``; an agent that passed ``id`` learned nothing from
   the refusal about which argument was wanted.
3. An approach record's ``route`` is capped at 500 characters by ``approach-record/v1``, and
   ``submit_approach_record``'s description did not say so.
"""

from __future__ import annotations

from typing import Any

from api_fakes import make_harness
from mcp_client import McpClient
from test_finding_queue_position import cold
from test_finding_submissions_mine import mine_doc
from test_pending_submissions import MERGE_SHA, annex, get

from opn_api.mcp import results, server
from opn_gate import schemas


def tool(name: str) -> Any:
    return next(t for t in server.TOOLS if t.name == name)


# --- 1. get_my_submissions with a finished submission ---------------------------------------------


def test_get_my_submissions_with_a_finished_submission_passes_its_own_schema() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    annex(h, alice)  # #1, merged below
    annex(h, alice)  # #2, still open
    h.githost.set_pull_request_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA)
    cold(h)
    get(h, "1")
    route = mine_doc(h, alice)
    assert [e["state"] for e in route["recent"]] == ["merged"]
    assert "automation" in route["recent"][0]  # the record as the routes serve it
    assert results.violations("get_my_submissions", route) == []
    over_mcp = McpClient(h).call("get_my_submissions", {}, token=alice)
    assert not over_mcp.isError, over_mcp.structuredContent
    assert over_mcp.structuredContent == route


# --- 2. get_submission's argument ----------------------------------------------------------------


def test_get_submission_with_id_is_refused_naming_submission_id() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    receipt = annex(h, alice)
    result = McpClient(h).call("get_submission", {"id": receipt["id"]})
    assert result.isError
    said = (result.structuredContent or {}).get("message", "") or " ".join(
        getattr(c, "text", "") for c in result.content
    )
    assert "submission_id" in said, said
    assert "`id`" in said, said  # names where the value comes from


def test_get_submission_takes_a_listings_id_as_submission_id() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice-p")
    receipt = annex(h, alice)
    doc = McpClient(h).ok("get_submission", {"submission_id": receipt["id"]})
    assert doc["submission"]["id"] == receipt["id"]


def test_get_submission_says_its_argument_is_the_id_the_listings_and_receipts_name() -> None:
    t = tool("get_submission")
    prop = t.input_schema["properties"]["submission_id"]["description"]
    for where in ("list_submissions", "receipts", "`id`"):
        assert where in prop, prop


# --- 3. the approach record's caps ---------------------------------------------------------------


def test_submit_approach_record_states_the_schemas_caps() -> None:
    props = schemas.load_schema("approach-record/v1")["properties"]
    said = tool("submit_approach_record").description
    caps = {
        "route": props["route"]["maxLength"],
        "blocked_on": props["blocked_on"]["maxLength"],
        "model_and_tooling": props["model_and_tooling"]["oneOf"][1]["maxLength"],
    }
    assert caps["route"] == 500  # the cap the agent hit
    for field, cap in caps.items():
        assert f"`{field}` {cap}" in said, said
    assert "characters" in said
