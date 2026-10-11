"""F06-T13 (audit 2026-10-04; testers 2026-10-01, bugs.md A14): a precheck on a hole whose witness
is already in an open pull request names that pull request.

While a hole's witness pull request was open, ``POST /precheck`` on the hole answered ``409
node-blocked … witness-missing … a witness goes in through POST /proposals/witness``, telling the
submitter to do what had been done (402-R2-a B1, 402-R6-a B2). The ``annex-pending`` refusal
(F06-T8) already names the open annex pull request a skeleton waits on; this one now does the
same, in the message and as ``details.pending``, found the same way: the service's own open
records.
"""

from __future__ import annotations

from api_fakes import Harness
from test_finding_mcp_bootstrap import HOLE, add_hole
from test_finding_precheck_blocked import bundle, nothing_started

from opn_api.store import Submission

TARGET = "propositional"


def witness_record(h: Harness, number: int = 41, node: str = HOLE) -> Submission:
    record = Submission(
        id=f"01M{number:023d}",
        kind="witness",
        node_id=node,
        target_id=TARGET,
        pr_number=number,
        pr_url=f"https://github.com/pr/{number}",
        pseudonym="bob-p",
        precheck_job_id=None,
        created="2026-10-01T12:00:00Z",
    )
    h.store.put_submission(record)
    return record


def precheck(h: Harness) -> dict[str, object]:
    token = h.token_for("code_alice", "alice-p")
    r = h.client.post(
        "/precheck", json={"node_id": HOLE, "bundle": bundle(HOLE)}, headers=h.auth(token)
    )
    body: dict[str, object] = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    return body


def test_an_open_witness_pull_request_is_named_not_asked_for_again(harness: Harness) -> None:
    add_hole(harness)
    record = witness_record(harness)
    body = precheck(harness)
    message = str(body["message"])
    assert f"#{record.pr_number}" in message, message
    assert "POST /proposals/witness" not in message, message
    details = body["details"]
    assert isinstance(details, dict)
    assert details["pending"] == {
        "kind": "witness",
        "id": record.id,
        "pr_number": record.pr_number,
        "pr_url": record.pr_url,
    }
    assert details["cause"] == "witness-missing"
    nothing_started(harness)


def test_with_no_open_witness_the_route_is_named_as_before(harness: Harness) -> None:
    add_hole(harness)
    witness_record(harness, node="some-other-node")  # another node's witness says nothing here
    body = precheck(harness)
    assert "/proposals/witness" in str(body["message"])
    details = body["details"]
    assert isinstance(details, dict) and details.get("pending") is None
