"""Claim refusals not yet named by a test (F05-R7, R8; D-25)."""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness

NODE = "and-reassoc"


def duplicate_node_in_another_target(harness: Harness) -> None:
    """Put a second frontier entry with the same node id under target ``other``, and drop the
    service's cached copy so the next read sees it."""
    doc = json.loads(harness.githost.files["frontier.json"])
    twin = {**next(e for e in doc["entries"] if e["node_id"] == NODE), "target_id": "other"}
    doc["entries"].append(twin)
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.context.files.pop("frontier.json", None)


def post(h: Harness, token: str, **body: Any) -> Any:
    return h.client.post("/claims", json={"node_id": NODE, **body}, headers=h.auth(token))


def test_target_id_shape_is_checked(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    for bad in ("Propositional", "a/b", "", 7, ["propositional"]):
        r = post(harness, token, target_id=bad)
        assert r.status_code == 400, bad
        assert r.json()["error"] == "target-id-invalid", bad
    assert harness.store.claims == {}


def test_node_in_two_targets_needs_a_target_id(harness: Harness) -> None:
    """R7: a node id that exists in several targets is ambiguous without ``target_id``; with
    one it resolves, and a target that does not hold the node is a 404."""
    token = harness.token_for("code_alice", "alice-p")
    duplicate_node_in_another_target(harness)
    ambiguous = post(harness, token)
    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"] == "node-ambiguous"

    resolved = post(harness, token, target_id="propositional")
    assert resolved.status_code == 201, resolved.text
    assert resolved.json()["target_id"] == "propositional"
    twin = post(harness, token, target_id="other")
    assert twin.status_code == 201
    assert twin.json()["target_id"] == "other"

    elsewhere = post(harness, token, target_id="nowhere")
    assert elsewhere.status_code == 404
    assert elsewhere.json()["error"] == "node-not-in-frontier"


def test_node_id_is_checked_before_the_ttl(harness: Harness) -> None:
    """The first violation is the one named: a bad node id with a bad TTL says node id."""
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="Bad", ttl_hours=999)
    assert r.status_code == 400
    assert r.json()["error"] == "node-id-invalid"


def test_ttl_is_checked_before_the_frontier_is_consulted(harness: Harness) -> None:
    """An over-cap TTL on an unknown node is refused for the TTL: no frontier read is needed to
    decide it, so the graph is not asked."""
    token = harness.token_for("code_alice", "alice-p")
    harness.githost.fetches.clear()
    r = post(harness, token, node_id="no-such-node", ttl_hours=999)
    assert r.status_code == 400
    assert r.json()["error"] == "ttl-above-cap"
    assert harness.githost.fetches == []


def test_releasing_twice_is_idempotent_and_keeps_the_first_time(harness: Harness) -> None:
    """R8: a released claim stays released; a second DELETE by the holder is 200 with the
    original release time, not a new one."""
    token = harness.token_for("code_alice", "alice-p")
    claim_id = post(harness, token).json()["id"]
    first = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(token))
    assert first.status_code == 200
    harness.clock.advance(minutes=5)
    second = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(token))
    assert second.status_code == 200
    assert second.json()["released"] == first.json()["released"] == "2026-09-09T12:00:00Z"
    assert harness.client.get("/claims.json").json()["nodes"][NODE]["history_count"] == 1


def test_releasing_an_expired_claim_is_allowed_and_recorded(harness: Harness) -> None:
    """Lazy expiry (R8) already treats it as released; the holder may still say so explicitly,
    and the record then carries the release time."""
    token = harness.token_for("code_alice", "alice-p")
    claim_id = post(harness, token, ttl_hours=1).json()["id"]
    harness.clock.advance(hours=2)
    r = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(token))
    assert r.status_code == 200
    assert r.json()["released"] == "2026-09-09T14:00:00Z"


def test_non_holder_cannot_release_a_claim_even_after_it_expired(harness: Harness) -> None:
    alice = harness.token_for("code_alice", "alice-p")
    bob = harness.token_for("code_bob", "bob-p")
    claim_id = post(harness, alice).json()["id"]
    harness.clock.advance(hours=2)
    r = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(bob))
    assert r.status_code == 403
    assert r.json()["error"] == "not-holder"


def test_expired_claims_do_not_count_toward_the_active_cap(harness: Harness) -> None:
    """AC14's cap counts *active* claims: once they expire, room opens without a release."""
    from api_fakes import make_harness  # noqa: PLC0415 — one use

    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1"})
    token = h.token_for("code_alice", "alice-p")
    assert post(h, token, ttl_hours=1).status_code == 201
    assert post(h, token).status_code == 429
    h.clock.advance(hours=1, seconds=1)
    assert post(h, token).status_code == 201


def test_claim_receipt_never_carries_the_identity_id(harness: Harness) -> None:
    """The overlay shows pseudonyms (R9); the receipt does too, and the ULID that keys the
    identities table stays inside the service."""
    token = harness.token_for("code_alice", "alice-p")
    receipt = post(harness, token).json()
    identity_id = next(iter(harness.store.identities))
    assert identity_id not in json.dumps(receipt)
    assert identity_id not in harness.client.get("/frontier.json").text
    assert identity_id not in harness.client.get("/claims.json").text
