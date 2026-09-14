"""Claim refusals not yet named by a test (F05-R7, R8; D-25)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import Harness

from opn_api import precheck
from opn_api.app import ApiError

NODE = "and-reassoc"
GRAPH_PATH = "targets/propositional/graph.json"


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

    # F05-T9: a target that does not hold the node is ``node-unknown`` (was node-not-in-frontier).
    elsewhere = post(harness, token, target_id="nowhere")
    assert elsewhere.status_code == 404
    assert elsewhere.json()["error"] == "node-unknown"
    assert "in target nowhere" in elsewhere.json()["message"]


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


# --- F05-T9: the edges of the refusal reasons -----------------------------------------------------


def edit_graph(harness: Harness, *rows: dict[str, Any], drop: str | None = None) -> None:
    """Add rows to (or drop one from) the committed graph.json, and forget the cached copies."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != drop] + [
        {
            "cause": None,
            "deps": [],
            "origin": "authored",
            "statement_hash": "3" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
            **row,
        }
        for row in rows
    ]
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.clear()


def test_a_node_under_a_refuted_dependency_names_the_cause_and_the_dependency(
    harness: Harness,
) -> None:
    """A refuted dependency is one of the unproved ones and ``dep-refuted`` is named with it; a
    proved dependency beside it is not listed, and no witness route is offered."""
    edit_graph(
        harness,
        {"node_id": "refuted-lemma", "status": "refuted"},
        {
            "node_id": "under-refuted",
            "status": "blocked",
            "cause": "dep-refuted",
            "deps": ["already-proved", "refuted-lemma"],
        },
    )
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="under-refuted")
    body = r.json()
    assert (r.status_code, body["error"]) == (409, "node-blocked"), r.text
    assert body["details"] == {
        "status": "blocked",
        "cause": "dep-refuted",
        "unproved_deps": ["refuted-lemma"],
    }
    assert "refuted-lemma" in body["message"] and "dep-refuted" in body["message"]
    assert "already-proved" not in body["message"]
    assert "/proposals/witness" not in body["message"]


def test_a_dependency_the_graph_lacks_is_listed_as_unproved(harness: Harness) -> None:
    """A dependency with no row cannot be taken as proved."""
    edit_graph(harness, {"node_id": "orphan-dep", "status": "blocked", "deps": ["gone-node"]})
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="orphan-dep")
    assert r.json()["details"]["unproved_deps"] == ["gone-node"], r.text


def test_a_blocked_node_with_no_cause_and_no_unproved_dependency_still_says_blocked(
    harness: Harness,
) -> None:
    edit_graph(harness, {"node_id": "odd-blocked", "status": "blocked", "deps": ["already-proved"]})
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="odd-blocked")
    body = r.json()
    assert (r.status_code, body["error"]) == (409, "node-blocked"), r.text
    assert body["details"] == {"status": "blocked", "cause": None, "unproved_deps": []}
    assert "names no cause" in body["message"]


def test_a_blocked_variant_on_the_frontier_is_refused_as_blocked(harness: Harness) -> None:
    """F03-T6: an open variant stays on the frontier while it waits on its holes, with
    ``claimable: false``. The refusal is the shared ``node-blocked`` naming what it waits on — not
    a bare ``node-not-claimable``, whose target reasons are empty on a claimable target."""
    doc = json.loads(harness.githost.files["frontier.json"])
    for e in doc["entries"]:
        if e["node_id"] == NODE:
            e["claimable"] = False
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    edit_graph(
        harness,
        {"node_id": "hole-1", "status": "blocked", "cause": "witness-missing"},
        {"node_id": NODE, "status": "blocked", "origin": "variant", "deps": ["hole-1"]},
        drop=NODE,
    )
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token)
    body = r.json()
    assert (r.status_code, body["error"]) == (409, "node-blocked"), r.text
    assert body["details"] == {"status": "blocked", "cause": None, "unproved_deps": ["hole-1"]}
    assert harness.store.claims == {}


def test_a_target_row_with_an_empty_reason_list_gives_the_bare_refusal(harness: Harness) -> None:
    """``listed-only`` is on the fixture frontier with ``claimable: false``; a row naming no
    reasons adds none to the message, and ``details.not_claimable`` is the empty list."""
    index = json.loads(harness.githost.files["targets/index.json"])
    for row in index["targets"]:
        row["not_claimable"] = []
    harness.githost.files["targets/index.json"] = json.dumps(index).encode()
    harness.context.files.clear()
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="listed-only")
    assert r.status_code == 409
    assert r.json() == {
        "error": "node-not-claimable",
        "message": "listed-only is not claimable",
        "details": {"not_claimable": []},
    }


def test_an_unreadable_targets_index_still_refuses_without_reasons(harness: Harness) -> None:
    """C7: the refusal is certain from the frontier; the reasons are what the index adds, so an
    index the service cannot read costs the reasons, not the answer."""
    del harness.githost.files["targets/index.json"]
    harness.context.files.clear()
    with pytest.raises(ApiError) as caught:
        precheck.index_doc(harness.context)
    assert (caught.value.status, caught.value.code) == (503, "graph-unreachable")

    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="listed-only")
    assert r.status_code == 409
    assert r.json()["details"] == {"not_claimable": []}


def test_node_facts_serves_a_frontier_node_the_graph_does_not_carry(harness: Harness) -> None:
    """The graph is read first; a node only the frontier lists keeps its frontier facts, with no
    status for a route to act on — so nothing refuses it as blocked, and it stays claimable."""
    edit_graph(harness, drop=NODE)
    facts = precheck.node_facts(harness.context, NODE)
    assert facts["target_id"] == "propositional"
    assert (facts["status"], facts["cause"], facts["deps"]) == (None, None, [])

    token = harness.token_for("code_alice", "alice-p")
    assert post(harness, token).status_code == 201


def test_node_facts_carries_what_the_graph_row_says(harness: Harness) -> None:
    facts = precheck.node_facts(harness.context, "already-proved")
    assert (facts["status"], facts["cause"], facts["deps"]) == ("proved", None, [])
    assert facts["proof_commit"] == "7" * 40


def test_a_refusal_without_details_renders_no_details_key(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    r = post(harness, token, node_id="no-such-node")
    assert r.status_code == 404
    assert set(r.json()) == {"error", "message"}
