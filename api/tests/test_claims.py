"""F05-T3: claims (R7, R8; AC9-AC14; D-25, Q1)."""

from __future__ import annotations

from api_fakes import Harness, make_harness

NODE = "and-reassoc"


def claim(h: Harness, token: str, **body: object) -> dict[str, object]:
    r = h.client.post("/claims", json={"node_id": NODE, **body}, headers=h.auth(token))
    assert r.status_code == 201, r.text
    doc: dict[str, object] = r.json()
    return doc


def test_ttl_caps(harness: Harness) -> None:
    """AC9: no TTL -> the minimum; 200 h -> 400; 24 h -> 24 h."""
    token = harness.token_for("code_alice", "alice-p")
    default = claim(harness, token)
    assert default["created"] == "2026-09-09T12:00:00Z"
    assert default["expires"] == "2026-09-09T13:00:00Z"

    over = harness.client.post(
        "/claims", json={"node_id": NODE, "ttl_hours": 200}, headers=harness.auth(token)
    )
    assert over.status_code == 400
    assert over.json()["error"] == "ttl-above-cap"

    day = claim(harness, token, ttl_hours=24)
    assert day["expires"] == "2026-09-10T12:00:00Z"

    # Below the minimum is clamped up, not refused (D-25: undeclared gets the minimum).
    assert claim(harness, token, ttl_hours=1)["expires"] == "2026-09-09T13:00:00Z"
    for bad in [0, -3, "24", 1.5, True]:
        r = harness.client.post(
            "/claims", json={"node_id": NODE, "ttl_hours": bad}, headers=harness.auth(token)
        )
        assert r.status_code == 400, bad
        assert r.json()["error"] == "ttl-invalid", bad


def test_only_claimable_nodes(harness: Harness) -> None:
    """AC10: absent from the frontier -> 404; present but not claimable -> 409."""
    token = harness.token_for("code_alice", "alice-p")
    absent = harness.client.post(
        "/claims", json={"node_id": "no-such-node"}, headers=harness.auth(token)
    )
    assert absent.status_code == 404
    assert absent.json()["error"] == "node-not-in-frontier"

    listed = harness.client.post(
        "/claims", json={"node_id": "listed-only"}, headers=harness.auth(token)
    )
    assert listed.status_code == 409
    assert listed.json()["error"] == "node-not-claimable"

    bad = harness.client.post("/claims", json={"node_id": "Not_An_Id"}, headers=harness.auth(token))
    assert bad.status_code == 400
    assert bad.json()["error"] == "node-id-invalid"


def test_racing_allowed(harness: Harness) -> None:
    """AC11: two identities may hold claims on one node, and the overlay lists both."""
    alice = harness.token_for("code_alice", "alice-p")
    bob = harness.token_for("code_bob", "bob-p")
    claim(harness, alice)
    claim(harness, bob, ttl_hours=24)
    entry = next(
        e for e in harness.client.get("/frontier.json").json()["entries"] if e["node_id"] == NODE
    )
    assert [a["pseudonym"] for a in entry["claims"]["active"]] == ["alice-p", "bob-p"]
    assert entry["claims"]["history_count"] == 2


def test_release_holder_only(harness: Harness) -> None:
    """AC12: another identity gets 403; the holder releases it and it leaves `active`."""
    alice = harness.token_for("code_alice", "alice-p")
    bob = harness.token_for("code_bob", "bob-p")
    receipt = claim(harness, alice)
    claim_id = str(receipt["id"])

    forbidden = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(bob))
    assert forbidden.status_code == 403
    assert forbidden.json()["error"] == "not-holder"

    released = harness.client.delete(f"/claims/{claim_id}", headers=harness.auth(alice))
    assert released.status_code == 200
    assert released.json()["released"] == "2026-09-09T12:00:00Z"
    assert harness.client.get("/claims.json").json()["nodes"][NODE] == {
        "active": [],
        "history_count": 1,
    }
    unknown = harness.client.delete("/claims/NOPE", headers=harness.auth(alice))
    assert unknown.status_code == 404


def test_lazy_expiry(harness: Harness) -> None:
    """AC13: past expiry the claim is absent from `active` but still counted in history."""
    token = harness.token_for("code_alice", "alice-p")
    claim(harness, token, ttl_hours=2)
    nodes = harness.client.get("/claims.json").json()["nodes"]
    assert len(nodes[NODE]["active"]) == 1

    harness.clock.advance(hours=2, seconds=1)
    after = harness.client.get("/claims.json").json()["nodes"]
    assert after[NODE] == {"active": [], "history_count": 1}
    entry = next(
        e for e in harness.client.get("/frontier.json").json()["entries"] if e["node_id"] == NODE
    )
    assert entry["claims"] == {"active": [], "history_count": 1}


def test_active_claim_cap() -> None:
    """AC14: a 21st active claim is 429; releasing one makes room again."""
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "3"})
    token = h.token_for("code_alice", "alice-p")
    receipts = [claim(h, token, ttl_hours=24) for _ in range(3)]
    over = h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(token))
    assert over.status_code == 429
    assert over.json()["error"] == "active-claims-cap"
    assert int(over.headers["retry-after"]) == 24 * 3600

    h.client.delete(f"/claims/{receipts[0]['id']}", headers=h.auth(token))
    assert (
        h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(token)).status_code == 201
    )


def test_cap_is_per_identity() -> None:
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1"})
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    claim(h, alice)
    assert (
        h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(alice)).status_code == 429
    )
    assert h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(bob)).status_code == 201


def test_receipt_names_the_target(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    receipt = claim(harness, token)
    assert receipt["target_id"] == "propositional"
    assert receipt["pseudonym"] == "alice-p"
    assert receipt["released"] is None
    assert len(str(receipt["id"])) == 26  # ULID (§6)
