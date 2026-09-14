"""Bench finding: one identity can hold two active claims on one node.

D-25 permits racing *between* identities ("Racing is permitted and on hard nodes desirable"),
and F05-R7 spells that out as "multiple identities may hold claims on one node" (AC11). A
claim is an advisory signal that an identity is working a node, carrying the TTL it declared
at claim time; nothing in D-25 or F05 lets one identity hold two, and a second one makes the
frontier overlay (F05-R9's ``claims.active``) report two workers where there is one. D-25
has no renewal or extension mechanism, so the correct answer to a repeat is a refusal, not a
silent extension: 409, naming the claim already held so the caller can release it first.

Not tested: ``DELETE`` on an already-released claim answering 200 with the original record.
F05-R8 says only "mark it released"; the handler keeps the first ``released`` timestamp, which
is an idempotent release, and neither D-25 nor F05 asks for a signal. That behaviour is correct
as written.
"""

from __future__ import annotations

import pytest
from api_fakes import Harness
from test_claims import NODE, claim


@pytest.mark.xfail(
    strict=True,
    reason=(
        "F14 bench finding: "
        "one identity may hold one live claim per node (D-25, F05-R7); fix: refuse or extend, and "
        "rewrite test_ttl_caps"
    ),
)
def test_same_identity_cannot_claim_a_node_twice(harness: Harness) -> None:
    """A second claim by the holder of an active claim is 409 and names the held claim."""
    alice = harness.token_for("code_alice", "alice-p")
    first = claim(harness, alice)

    again = harness.client.post("/claims", json={"node_id": NODE}, headers=harness.auth(alice))
    assert again.status_code == 409, again.text
    body = again.json()
    assert body["error"] == "claim-already-held"
    assert str(first["id"]) in body["message"]


@pytest.mark.xfail(
    strict=True,
    reason=("F14 bench finding: follows the same fix"),
)
def test_overlay_lists_an_identity_once_per_node(harness: Harness) -> None:
    """Whatever the second request answers, the overlay shows one active claim for alice."""
    alice = harness.token_for("code_alice", "alice-p")
    claim(harness, alice)
    harness.client.post(
        "/claims", json={"node_id": NODE, "ttl_hours": 24}, headers=harness.auth(alice)
    )
    entry = next(
        e for e in harness.client.get("/frontier.json").json()["entries"] if e["node_id"] == NODE
    )
    assert [a["pseudonym"] for a in entry["claims"]["active"]] == ["alice-p"]
    assert entry["claims"]["history_count"] == 1


def test_a_released_claim_does_not_block_a_new_one(harness: Harness) -> None:
    """Edge: once released (or expired), the same identity may claim the node again."""
    alice = harness.token_for("code_alice", "alice-p")
    first = claim(harness, alice)
    harness.client.delete(f"/claims/{first['id']}", headers=harness.auth(alice))
    claim(harness, alice)
    harness.clock.advance(hours=1, seconds=1)
    claim(harness, alice)
