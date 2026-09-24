"""F07-T41 (testers 2026-09-24): a proposal's submission shows the statement it proposes.

The story. Both erdos-402 agents proposed variants for the same cases (|A| = 6 and 7) within
minutes of each other. At 12:40Z the HTTP agent read ``GET /submissions/<id>`` for the other's
#189, and at 12:48Z the MCP agent read ``get_submission`` for #188 and #190
(``engineering/evidence/testers-2026-09-24/erdos-402-http.md:39`` and ``erdos-402-mcp.md:49``):
each answer carried ids, a node id and the pull request's state, and not one line of Lean, so
neither could tell whether the other's proposal duplicated its own without leaving the network
for GitHub. Both then proposed anyway, and #189 and #198 later failed the gate on
``declaration-clash`` against #188 and #190.

The mechanism. A proposal's record (``kind`` ``speculative`` or ``variant``) keeps what the
pull request was, not what it proposes. The statement exists only on the branch, as
``targets/<t>/nodes/<id>/Statement.lean`` at the pull request's head commit, which the service
never read back.

The rule. ``GET /submissions/<id>`` for a proposal carries ``proposed_statement``: the branch's
``Statement.lean`` read at the head commit (``{path, head_sha, text, truncated}``, the text capped
at 16 kB), with ``proposed_statement_error`` naming why it is ``null`` when the host cannot say.
Both sit outside the ``submission`` document, so ``GET /submissions.json`` entries still equal
the per-id documents byte for byte. A non-proposal carries neither key.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_pending_submissions import record

from opn_api.mcp import results

NEW_NODE = "variant-e6d83e6d"
TARGET = "propositional"
HEAD = "e" * 40
PATH = f"targets/{TARGET}/nodes/{NEW_NODE}/Statement.lean"
STATEMENT = (
    "import Targets.Propositional.Context\n\n"
    "theorem Opn.erdos_402_card_six : 6 = 6 := by\n  sorry\n"
)
CAP = 16 * 1024


def open_proposal(h: Harness, kind: str = "variant", number: int = 188) -> None:
    h.store.put_submission(record(number, kind=kind, node_id=NEW_NODE))
    h.githost.set_pull_request_state(number, head_sha=HEAD, mergeable_state="behind")
    h.githost.files_at[HEAD] = {PATH: STATEMENT.encode()}


def get(h: Harness, number: int) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
@pytest.mark.parametrize("kind", ["variant", "speculative"])
def test_a_variant_submission_carries_its_statement_at_the_head_sha(
    harness: Harness, kind: str
) -> None:
    open_proposal(harness, kind)
    doc = get(harness, 188)
    assert doc.get("proposed_statement") == {
        "path": PATH,
        "head_sha": HEAD,
        "text": STATEMENT,
        "truncated": False,
    }, doc
    assert doc.get("proposed_statement_error", "absent") is None
    assert HEAD in harness.githost.refs  # read at the head commit, not at main


def test_a_proof_submission_has_no_statement_key(harness: Harness) -> None:
    for number, kind in ((3, "proof"), (4, "annex"), (5, "witness")):
        harness.store.put_submission(record(number, kind=kind, node_id=NEW_NODE))
        doc = get(harness, number)
        assert "proposed_statement" not in doc and "proposed_statement_error" not in doc, doc


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
def test_a_host_failure_gives_null_with_the_reason(harness: Harness) -> None:
    open_proposal(harness)
    harness.githost.unreachable = True
    doc = get(harness, 188)
    assert "proposed_statement" in doc and doc["proposed_statement"] is None, doc
    assert "ConnectError" in str(doc.get("proposed_statement_error")), doc


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
def test_a_branch_without_the_file_gives_null_with_the_reason(harness: Harness) -> None:
    open_proposal(harness)
    harness.githost.files_at[HEAD] = {}
    harness.githost.absent_at[HEAD] = {PATH}
    doc = get(harness, 188)
    assert "proposed_statement" in doc and doc["proposed_statement"] is None, doc
    assert "404" in str(doc.get("proposed_statement_error")), doc


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
def test_a_long_statement_is_capped_at_16_kb_and_says_so(harness: Harness) -> None:
    open_proposal(harness)
    harness.githost.files_at[HEAD] = {PATH: (STATEMENT + "-- " + "x" * CAP + "\n").encode()}
    shown = get(harness, 188).get("proposed_statement") or {}
    assert shown.get("truncated") is True, shown
    assert len(str(shown.get("text")).encode()) <= CAP
    assert str(shown.get("text")).startswith(STATEMENT)


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
def test_the_list_entry_still_equals_the_document(harness: Harness) -> None:
    """The pinned equality between ``submissions.json`` and the per-id ``submission`` holds: the
    statement rides beside the document, never inside it."""
    open_proposal(harness)
    doc = get(harness, 188)
    [entry] = harness.client.get("/submissions.json").json()["open"]
    assert entry == doc["submission"]
    assert "proposed_statement" not in doc["submission"]
    assert "proposed_statement" in doc


@pytest.mark.xfail(
    strict=True, reason="F07-T41: a proposal's record never reads its statement back"
)
def test_mcp_get_submission_carries_the_statement_and_validates(harness: Harness) -> None:
    open_proposal(harness)
    over_http = get(harness, 188)
    assert results.violations("get_submission", over_http) == []
    assert McpClient(harness).ok("get_submission", {"submission_id": "188"}) == over_http
    assert "proposed_statement" in over_http
    props = results.load("get_submission")["oneOf"][0]["properties"]
    assert {"proposed_statement", "proposed_statement_error"} <= set(props)
