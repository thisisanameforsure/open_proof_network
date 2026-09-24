"""F05-T3: claims (R7, R8; AC9-AC14; D-25, Q1)."""

from __future__ import annotations

from api_fakes import Harness, make_harness

NODE = "and-reassoc"


def claim(h: Harness, token: str, **body: object) -> dict[str, object]:
    r = h.client.post("/claims", json={"node_id": NODE, **body}, headers=h.auth(token))
    assert r.status_code == 201, r.text
    doc: dict[str, object] = r.json()
    return doc


def release(h: Harness, token: str, receipt: dict[str, object]) -> None:
    r = h.client.delete(f"/claims/{receipt['id']}", headers=h.auth(token))
    assert r.status_code == 200, r.text


def test_ttl_caps(harness: Harness) -> None:
    """AC9: no TTL -> the minimum; 200 h -> 400; 24 h -> 24 h.

    Each claim is released before the next: since F05-T14 a repeat on a node already held
    returns that claim, TTL unchanged (``test_finding_claim_twice.py``)."""
    token = harness.token_for("code_alice", "alice-p")
    default = claim(harness, token)
    assert default["created"] == "2026-09-09T12:00:00Z"
    assert default["expires"] == "2026-09-09T13:00:00Z"
    release(harness, token, default)

    over = harness.client.post(
        "/claims", json={"node_id": NODE, "ttl_hours": 200}, headers=harness.auth(token)
    )
    assert over.status_code == 400
    assert over.json()["error"] == "ttl-above-cap"

    day = claim(harness, token, ttl_hours=24)
    assert day["expires"] == "2026-09-10T12:00:00Z"
    release(harness, token, day)

    # Below the minimum is clamped up, not refused (D-25: undeclared gets the minimum).
    assert claim(harness, token, ttl_hours=1)["expires"] == "2026-09-09T13:00:00Z"
    for bad in [0, -3, "24", 1.5, True]:
        r = harness.client.post(
            "/claims", json={"node_id": NODE, "ttl_hours": bad}, headers=harness.auth(token)
        )
        assert r.status_code == 400, bad
        assert r.json()["error"] == "ttl-invalid", bad


def test_only_claimable_nodes(harness: Harness) -> None:
    """AC10: not a node of the graph -> 404; present but not claimable -> 409.

    Rewritten for F05-T9: the 404 was ``node-not-in-frontier`` for any node off the frontier;
    a node the graph does not have is now ``node-unknown``, and blocked or proved nodes get
    their own 409s (``test_finding_refusal_reasons.py``)."""
    token = harness.token_for("code_alice", "alice-p")
    absent = harness.client.post(
        "/claims", json={"node_id": "no-such-node"}, headers=harness.auth(token)
    )
    assert absent.status_code == 404
    assert absent.json()["error"] == "node-unknown"

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


OTHER_NODE = "tutorial-and-swap"  # the fixture frontier's other claimable node


def test_active_claim_cap() -> None:
    """AC14: a 21st active claim is 429; releasing one makes room again.

    Since F05-T14 one holder has one claim per node, so the cap is reached across nodes: a cap
    of one, a claim on NODE, and a claim on the fixture's other claimable node is the one over."""
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1"})
    token = h.token_for("code_alice", "alice-p")
    held = claim(h, token, ttl_hours=24)
    over = h.client.post("/claims", json={"node_id": OTHER_NODE}, headers=h.auth(token))
    assert over.status_code == 429
    assert over.json()["error"] == "active-claims-cap"
    assert int(over.headers["retry-after"]) == 24 * 3600

    h.client.delete(f"/claims/{held['id']}", headers=h.auth(token))
    assert (
        h.client.post("/claims", json={"node_id": OTHER_NODE}, headers=h.auth(token)).status_code
        == 201
    )


def test_cap_is_per_identity() -> None:
    h = make_harness({"OPN_API_ACTIVE_CLAIMS": "1"})
    alice = h.token_for("code_alice", "alice-p")
    bob = h.token_for("code_bob", "bob-p")
    claim(h, alice)
    assert (
        h.client.post("/claims", json={"node_id": OTHER_NODE}, headers=h.auth(alice)).status_code
        == 429
    )
    assert h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(bob)).status_code == 201


def test_receipt_names_the_target(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    receipt = claim(harness, token)
    assert receipt["target_id"] == "propositional"
    assert receipt["pseudonym"] == "alice-p"
    assert receipt["released"] is None
    assert len(str(receipt["id"])) == 26  # ULID (§6)


# --- F14-R1 (was F11-AC6): a listed target's nodes are claimable; a frozen one's are not ---------

LISTED_NODE = "listed-lemma"


def serve_listed(h: Harness) -> None:
    """Put the products of a *curated but listed* target in front of the service.

    The two documents are generated by the gate itself (`gate/tests/harness.take_in` through
    `products.generate`) rather than written by hand, so this test cannot pass against a shape the
    gate does not produce — the F05-Q5 rule that the api's fixtures are copied from a golden.
    """
    from pathlib import Path  # noqa: PLC0415

    fixtures = Path(__file__).resolve().parent / "fixtures"
    h.githost.files["frontier.json"] = (fixtures / "frontier-listed.json").read_bytes()
    h.githost.files["targets/index.json"] = (fixtures / "targets-index-listed.json").read_bytes()
    h.context.files.clear()  # drop the cached copy of the old frontier


FROZEN_NODE = "frozen-lemma"


def serve_frozen(h: Harness) -> None:
    """Put the products of a curated target whose root carries an upstream-drift flag in front of
    the service: since F14-R1 the one reason, besides a closed status, a curated target is not
    claimable. Generated by the gate like the listed pair (F05-Q5; recipe in
    engineering/evidence/F12/task-6.txt, plus ``harness.freeze_upstream``)."""
    from pathlib import Path  # noqa: PLC0415

    fixtures = Path(__file__).resolve().parent / "fixtures"
    h.githost.files["frontier.json"] = (fixtures / "frontier-frozen.json").read_bytes()
    h.githost.files["targets/index.json"] = (fixtures / "targets-index-frozen.json").read_bytes()
    h.context.files.clear()


STEWARDLESS_NODE = "stewardless-lemma"


def serve_stewardless(h: Harness) -> None:
    """F15-R4: the products of an open-track target with no steward while the graph's policy.json
    enforces the steward rule — generated by the gate like the other pairs
    (``api/tests/test_fixture_is_golden.py`` is the recipe)."""
    from pathlib import Path  # noqa: PLC0415

    fixtures = Path(__file__).resolve().parent / "fixtures"
    h.githost.files["frontier.json"] = (fixtures / "frontier-stewardless.json").read_bytes()
    h.githost.files["targets/index.json"] = (
        fixtures / "targets-index-stewardless.json"
    ).read_bytes()
    h.context.files.clear()


def test_a_stewardless_open_target_refuses_claims_under_the_rule(harness: Harness) -> None:
    """F15-R4 (T4): the api reads the index as today — ``no-steward`` arrives as the reason on
    the 409, in the words the Targets page uses, and the policy state rides at the top."""
    serve_stewardless(harness)
    served = harness.client.get("/frontier.json").json()
    entry = next(e for e in served["entries"] if e["node_id"] == STEWARDLESS_NODE)
    assert entry["claimable"] is False and entry["dormant"] is False

    token = harness.token_for("code_alice", "alice-p")
    refused = harness.client.post(
        "/claims", json={"node_id": STEWARDLESS_NODE}, headers=harness.auth(token)
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"] == "node-not-claimable"
    assert refused.json()["details"]["not_claimable"] == ["no-steward"]
    assert "no steward has committed" in refused.json()["message"]
    index = harness.client.get("/targets/index.json")
    if index.status_code == 200:
        doc = index.json()
        assert doc["policy"]["steward_rule"]["enforced"] is True
        row = next(t for t in doc["targets"] if t["target_id"] == "stewardless-target")
        assert row["claimable"] is False and row["stewards"] == []


def test_listed_is_claimable(harness: Harness) -> None:
    """F14-R1 (replacing AC6's refusal): a listed target nobody has signed or posted is open for
    work — its node carries claimable: true and POST /claims on it is a 201."""
    serve_listed(harness)
    served = harness.client.get("/frontier.json").json()
    assert served["schema"] == "frontier/v3"  # the service serves the version the graph published
    entry = next(e for e in served["entries"] if e["node_id"] == LISTED_NODE)
    assert entry["claimable"] is True and entry["dormant"] is False

    token = harness.token_for("code_alice", "alice-p")
    made = harness.client.post(
        "/claims", json={"node_id": LISTED_NODE}, headers=harness.auth(token)
    )
    assert made.status_code == 201, made.text

    index = harness.client.get("/targets/index.json")
    if index.status_code == 200:  # the plain path exists only where F05 publishes it
        row = next(t for t in index.json()["targets"] if t["target_id"] == "listed-target")
        assert row["claimable"] is True and row["not_claimable"] == []


def test_a_frozen_target_is_not_claimable(harness: Harness) -> None:
    """F14-R1, F12-R11: an upstream edit flagged on the root freezes claiming — claimable: false
    on the entry, and POST /claims is a 409 naming the drift."""
    serve_frozen(harness)
    served = harness.client.get("/frontier.json").json()
    entry = next(e for e in served["entries"] if e["node_id"] == FROZEN_NODE)
    assert entry["claimable"] is False

    token = harness.token_for("code_alice", "alice-p")
    refused = harness.client.post(
        "/claims", json={"node_id": FROZEN_NODE}, headers=harness.auth(token)
    )
    assert refused.status_code == 409
    assert refused.json()["error"] == "node-not-claimable"
    assert refused.json()["details"]["not_claimable"] == ["upstream-drift"]
