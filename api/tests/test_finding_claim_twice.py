"""F05-T14 (Q15): one claim per holder per node, and the receipt says who else is there.

The story. Six agents on the three calibration targets, 2026-09-24 12:24-13:25Z
(``engineering/session-notes/2026-09-24-calibration-testers.md``, finding 3). Two of them
(69-HTTP and 402-MCP) sent ``POST /claims`` twice for the same node under the same pseudonym and
got two ``201``s with two ids: the frontier's overlay then listed the one agent twice as if two
people were working on it. And on erdos-402 two agents claimed the same five variants nine seconds
apart, because the receipt is the claim alone: nothing in the answer said another pseudonym already
held the node, so each learned about the other only by reading the frontier afterwards.

The mechanism. ``claims.post_claims`` checked the per-identity active-claim cap and nothing else,
so the same identity's second call minted a new ``Claim``; and ``receipt`` carried the caller's
claim only.

The rule (D-25 stays: claims are advisory and non-exclusive, and racing across holders is allowed).
A second ``POST /claims`` by the same identity on the same node while its claim is active answers
``200`` with that claim, same id, unchanged; once released or expired, a new claim is a new id.
Every ``POST /claims`` receipt carries ``others``: the other active holders of the node
(``pseudonym``, ``expires``), never the caller, never an expired or released claim. The public
``claims.json`` (``claims/v1``, hash-pinned) does not change.

Every test runs on both stores (the both-stores rule, conventions §1): the rule reads the store.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_store_seam import dynamo

from opn_api.store import MemoryStore

NODE = "and-reassoc"


@pytest.fixture(params=["memory", "dynamodb"])
def h(request: pytest.FixtureRequest) -> Iterator[Harness]:
    store = MemoryStore() if request.param == "memory" else dynamo()
    harness = make_harness(store=store)
    with harness.client:
        yield harness


def post(h: Harness, token: str, **body: object) -> Any:
    return h.client.post("/claims", json={"node_id": NODE, **body}, headers=h.auth(token))


def active(h: Harness) -> list[dict[str, Any]]:
    doc: list[dict[str, Any]] = h.client.get("/claims.json").json()["nodes"][NODE]["active"]
    return doc


def test_the_same_holder_claiming_twice_gets_the_same_claim(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    first = post(h, alice, ttl_hours=5)
    assert first.status_code == 201, first.text
    h.clock.advance(minutes=3)
    again = post(h, alice, ttl_hours=24)
    assert again.status_code == 200, again.text
    assert again.json()["id"] == first.json()["id"]
    # the claim as it stands, not a new one with the second call's TTL
    assert again.json()["expires"] == first.json()["expires"] == "2026-09-09T17:00:00Z"
    assert again.json()["created"] == first.json()["created"]
    assert [a["pseudonym"] for a in active(h)] == ["alice-p"]
    assert len(h.store.list_claims()) == 1
    assert h.client.get("/claims.json").json()["nodes"][NODE]["history_count"] == 1


def test_claiming_again_at_the_cap_returns_the_claim_rather_than_429() -> None:
    """The cap counts claims, and a repeat makes none, so it is not charged against it."""
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1"})
    alice = h.token_for("code_alice", "alice-p")
    first = post(h, alice)
    again = post(h, alice)
    assert again.status_code == 200, again.text
    assert again.json()["id"] == first.json()["id"]


def test_after_release_a_new_claim_is_a_new_id(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    first = post(h, alice).json()
    released = h.client.delete(f"/claims/{first['id']}", headers=h.auth(alice))
    assert released.status_code == 200
    h.clock.advance(seconds=1)
    second = post(h, alice)
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first["id"]
    assert second.json()["released"] is None
    assert [a["pseudonym"] for a in active(h)] == ["alice-p"]


def test_an_expired_claim_does_not_count_as_held(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    first = post(h, alice, ttl_hours=2).json()
    h.clock.advance(hours=2, seconds=1)
    second = post(h, alice)
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first["id"]
    assert second.json()["expires"] == "2026-09-09T15:00:01Z"


def test_the_receipt_lists_other_active_holders_and_not_the_caller(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    mine = post(h, alice, ttl_hours=5).json()
    assert mine.get("others") == []
    theirs = post(h, bob, ttl_hours=24)
    assert theirs.status_code == 201, theirs.text
    assert theirs.json().get("others") == [
        {"pseudonym": "alice-p", "expires": "2026-09-09T17:00:00Z"}
    ]
    again = post(h, alice).json()
    assert again["id"] == mine["id"]
    assert again.get("others") == [{"pseudonym": "bob-p", "expires": "2026-09-10T12:00:00Z"}]


def test_the_receipt_omits_expired_and_released_holders(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    gone = post(h, alice, ttl_hours=1).json()
    h.client.delete(f"/claims/{gone['id']}", headers=h.auth(alice))
    assert post(h, bob, ttl_hours=1).json().get("others") == []
    # alice again, for an hour; bob's hour then runs out
    h.clock.advance(minutes=30)
    back = post(h, alice, ttl_hours=1).json()
    assert back.get("others") == [{"pseudonym": "bob-p", "expires": "2026-09-09T13:00:00Z"}]
    h.clock.advance(minutes=31)
    assert post(h, alice).json().get("others") == []


def test_racing_is_still_allowed_across_holders(h: Harness) -> None:
    """D-25: non-exclusive. Two identities, two claims, two ids, both in the overlay."""
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    a = post(h, alice)
    b = post(h, bob)
    assert (a.status_code, b.status_code) == (201, 201)
    assert a.json()["id"] != b.json()["id"]
    assert sorted(x["pseudonym"] for x in active(h)) == ["alice-p", "bob-p"]
