"""F06-T13 follow-up (audit 2026-10-04): a claim on a hole whose witness is already in an open pull
request names that pull request, as a precheck on it does since d71e28c.

``POST /claims`` refuses a blocked node through ``precheck.blocked_error`` from two places: a hole
the frontier does not list (``claims.off_frontier``), and one it lists with ``claimable: false``
(``claims.unclaimable``, the frontier/v4 shape of a hole waiting for its witness, F03-T16). Both
said "a witness goes in through POST /proposals/witness" to a caller whose witness was already
open. Each now passes ``pending_witness`` the way ``precheck.check_open`` does.
"""

from __future__ import annotations

import json

from api_fakes import Harness
from test_finding_mcp_bootstrap import HOLE, add_hole
from test_finding_precheck_witness_pending import witness_record
from test_rejections_claims import NODE, edit_graph

PENDING_KEYS = ("kind", "id", "pr_number", "pr_url")


def claim(h: Harness, node: str) -> dict[str, object]:
    token = h.token_for("code_alice", "alice-p")
    r = h.client.post("/claims", json={"node_id": node}, headers=h.auth(token))
    body: dict[str, object] = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    assert h.store.claims == {}
    return body


def names_the_open_witness(body: dict[str, object], number: int) -> None:
    message = str(body["message"])
    assert f"#{number}" in message, message
    assert "POST /proposals/witness" not in message, message
    details = body["details"]
    assert isinstance(details, dict)
    assert details["cause"] == "witness-missing"
    pending = details.get("pending")
    assert isinstance(pending, dict), details
    assert pending["pr_number"] == number
    assert tuple(pending) == PENDING_KEYS


def test_a_hole_off_the_frontier_names_its_open_witness(harness: Harness) -> None:
    add_hole(harness)
    record = witness_record(harness)
    names_the_open_witness(claim(harness, HOLE), record.pr_number)


def test_a_listed_hole_waiting_for_its_witness_names_it(harness: Harness) -> None:
    """frontier/v4: the hole is listed, ``claimable: false``, ``needs: witness``."""
    doc = json.loads(harness.githost.files["frontier.json"])
    for e in doc["entries"]:
        if e["node_id"] == NODE:
            e["claimable"] = False
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.context.files.pop("frontier.json", None)
    edit_graph(
        harness,
        {"node_id": NODE, "status": "blocked", "cause": "witness-missing", "deps": []},
        drop=NODE,
    )
    record = witness_record(harness, number=42, node=NODE)
    names_the_open_witness(claim(harness, NODE), record.pr_number)


def test_with_no_open_witness_the_route_is_named_as_before(harness: Harness) -> None:
    add_hole(harness)
    witness_record(harness, node="some-other-node")
    body = claim(harness, HOLE)
    assert "/proposals/witness" in str(body["message"])
    details = body["details"]
    assert isinstance(details, dict) and "pending" not in details
