"""F05: a claim receipt names the node's open submissions, not only its other holders.

The story. Tester agents, 2026-09-27: one agent claimed h2 and h3 on erdos-1050 while another
pseudonym already had witness pull requests open on both. The receipt said ``others: []``,
because the other pseudonym had never claimed; it had submitted. A claim is advisory (D-25,
F05-Q1), so the receipt is the one place the claimer learns what it is racing, and a pull
request already open on the node is the strongest thing it could be racing.

The rule. Every claim receipt (``POST /claims``, the repeat's ``200``, ``GET /claims/mine``)
carries ``open_submissions``: the service's open records on the claimed node, each with
``pr_number``, ``pr_url``, ``kind``, ``pseudonym`` and ``created``, oldest first, including the
caller's own (it is still a pull request on the node). A record the host has found merged or
closed is not listed. Nothing is refused: racing stays allowed.
"""

from __future__ import annotations

from typing import Any

from api_fakes import Harness

from opn_api import clock as clockmod
from opn_api.store import Submission

NODE = "and-reassoc"
TARGET = "propositional"


def record(h: Harness, number: int, *, node: str = NODE, kind: str = "witness") -> Submission:
    found = Submission(
        id=f"01M0000000000000000000000{number}",
        kind=kind,
        node_id=node,
        target_id=TARGET,
        pr_number=number,
        pr_url=f"https://github.com/pr/{number}",
        pseudonym="bob-p",
        precheck_job_id=None,
        created=clockmod.render(h.clock.now()),
    )
    h.store.put_submission(found)
    h.githost.set_pull_request_state(number)  # the host says open
    return found


def claim(h: Harness, token: str) -> Any:
    return h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(token))


def test_a_claim_receipt_names_the_open_pull_requests_on_the_node(harness: Harness) -> None:
    record(harness, 1)
    record(harness, 2, node="tutorial-and-swap")  # another node: not listed
    alice = harness.token_for("code_alice", "alice-p")
    r = claim(harness, alice)
    assert r.status_code == 201, r.text
    assert r.json()["others"] == []  # bob never claimed: the old receipt said nothing
    assert r.json().get("open_submissions") == [
        {
            "pr_number": 1,
            "pr_url": "https://github.com/pr/1",
            "kind": "witness",
            "pseudonym": "bob-p",
            "created": "2026-09-09T12:00:00Z",
        }
    ]


def test_the_repeat_and_claims_mine_carry_it_too(harness: Harness) -> None:
    alice = harness.token_for("code_alice", "alice-p")
    first = claim(harness, alice)
    assert first.json().get("open_submissions") == []
    record(harness, 1)
    again = claim(harness, alice)
    assert again.status_code == 200, again.text
    assert [s["pr_number"] for s in again.json().get("open_submissions") or []] == [1]
    mine = harness.client.get("/claims/mine", headers=harness.auth(alice)).json()
    assert [s["pr_number"] for s in mine["claims"][0].get("open_submissions") or []] == [1]


def test_a_merged_pull_request_is_not_listed(harness: Harness) -> None:
    record(harness, 1)
    harness.githost.set_pull_request_state(1, state="closed", merged=True)
    alice = harness.token_for("code_alice", "alice-p")
    r = claim(harness, alice)
    assert r.status_code == 201, r.text
    assert r.json().get("open_submissions") == []
