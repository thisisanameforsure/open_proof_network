"""mcpfix (lead; verifier VC, item 2, 2026-11-25): a claim on a hole whose witness has merged and
is not rendered yet says so, instead of asking for the witness again.

VC's witness #2062 merged at 15:41:57Z; at 15:43Z ``claim_node`` answered ``node-blocked``: "its
witness slot is empty, and a witness goes in through POST /proposals/witness" — the act VC had
just completed. The products lag a merge by about fourteen minutes. The refusal now names the
merged pull request and how long to wait, as ``products-pending`` does."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from api_fakes import Harness
from test_finding_claim_witness_pending import claim
from test_finding_mcp_bootstrap import HOLE, add_hole
from test_finding_precheck_witness_pending import witness_record

from opn_api import clock as clockmod

RENDERED = "5" * 40  # the fixture's rendered_from
MERGE = "9" * 40


def merged_witness(h: Harness, *, rendered: bool) -> int:
    record = witness_record(h, number=2062)
    merged_at = clockmod.render(h.clock.now() - timedelta(minutes=1))
    h.store.put_submission(
        replace(
            record,
            closed=merged_at,
            final_state={"merged": True, "merge_commit_sha": MERGE, "merged_at": merged_at},
        )
    )
    h.store.note_merged(record.pr_number, h.clock.now() + timedelta(hours=1))
    h.githost.ancestry[(MERGE, RENDERED)] = rendered
    return record.pr_number


def test_a_merged_witness_awaiting_render_is_named(harness: Harness) -> None:
    add_hole(harness)
    number = merged_witness(harness, rendered=False)
    body = claim(harness, HOLE)
    message = str(body["message"])
    assert f"#{number}" in message and "merged" in message, message
    assert "POST /proposals/witness" not in message, message
    details = body["details"]
    assert isinstance(details, dict)
    assert details["merged_witness"]["pr_number"] == number
    assert isinstance(details["retry_after_s"], int) and details["retry_after_s"] > 0


def test_once_rendered_the_graph_decides(harness: Harness) -> None:
    """A merge the products carry is not pending: the committed graph's word stands."""
    add_hole(harness)
    merged_witness(harness, rendered=True)
    message = str(claim(harness, HOLE)["message"])
    assert "POST /proposals/witness" in message
