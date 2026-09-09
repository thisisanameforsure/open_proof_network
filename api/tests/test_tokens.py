"""F05-T2: identity proof and token issuance (R3, R4; AC1-AC5)."""

from __future__ import annotations

import json
import logging

import pytest
from api_fakes import FAKE_ACCESS_TOKEN, Harness, alice, make_harness

from opn_api import auth, identity


def start_and_callback(h: Harness, code: str = "code_alice") -> dict[str, object]:
    start = h.client.get("/auth/github/start", follow_redirects=False)
    assert start.status_code == 302
    location = start.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=Iv1.test" in location
    state = location.split("state=")[1].split("&")[0]
    r = h.client.get(
        "/auth/github/callback",
        params={"code": code, "state": state},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200, r.text
    doc: dict[str, object] = r.json()
    return doc


def test_github_proof_issues_token(harness: Harness) -> None:
    """AC1: the flow yields an identity and a token, shown once."""
    proof = start_and_callback(harness)
    assert proof["login"] == "alice"
    r = harness.client.post(
        "/tokens",
        json={
            "proof": proof["proof"],
            "pseudonym": "alice-p",
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    token = doc["token"]
    assert isinstance(token, str) and len(token) >= 40
    assert doc["identity"]["pseudonym"] == "alice-p"
    assert doc["identity"]["proof_kind"] == "github"
    assert doc["identity"]["created"] == "2026-09-09T12:00:00Z"

    stored = harness.store.identities[doc["identity"]["id"]]
    assert stored.proof_reference == "alice"
    # Shown once: the proof is consumed, so the same proof cannot mint a second token.
    again = harness.client.post(
        "/tokens",
        json={
            "proof": proof["proof"],
            "pseudonym": "alice-q",
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )
    assert again.status_code == 400
    assert again.json()["error"] == "proof-invalid"


def test_dco_required(harness: Harness) -> None:
    """AC2: no DCO or a stale version -> 400 naming DCO, and nothing is stored."""
    proof = start_and_callback(harness)
    body = {"proof": proof["proof"], "pseudonym": "alice-p"}
    r = harness.client.post("/tokens", json=body)
    assert r.status_code == 400
    assert r.json()["error"] == "dco-not-accepted"

    stale = harness.client.post(
        "/tokens", json={**body, "dco": {"version": "0" * 16, "accepted": True}}
    )
    assert stale.status_code == 400
    assert stale.json()["error"] == "dco-version-stale"
    assert harness.store.identities == {}
    assert harness.store.tokens == {}


def test_dco_document_is_served(harness: Harness) -> None:
    r = harness.client.get("/dco.json")
    assert r.status_code == 200
    assert r.json()["version"] == identity.DCO_VERSION
    assert "Developer Certificate of Origin" in r.json()["text"]


def test_pseudonym_unique_case_insensitive(harness: Harness) -> None:
    """AC3: `Alice-P` taken -> `alice-p` is 409; the proof survives for another try."""
    harness.token_for("code_alice", "Alice-P")
    proof = start_and_callback(harness, "code_bob")
    body = {
        "proof": proof["proof"],
        "pseudonym": "alice-p",
        "dco": {"version": identity.DCO_VERSION, "accepted": True},
    }
    r = harness.client.post("/tokens", json=body)
    assert r.status_code == 409
    assert r.json()["error"] == "pseudonym-taken"
    retry = harness.client.post("/tokens", json={**body, "pseudonym": "bob-p"})
    assert retry.status_code == 201, retry.text


def test_pseudonym_shape(harness: Harness) -> None:
    proof = start_and_callback(harness)
    for bad in ["", "a" * 40, "alice p", "alice_p", "alice.p", 7]:
        r = harness.client.post(
            "/tokens",
            json={
                "proof": proof["proof"],
                "pseudonym": bad,
                "dco": {"version": identity.DCO_VERSION, "accepted": True},
            },
        )
        assert r.status_code == 400, bad
        assert r.json()["error"] == "pseudonym-invalid", bad


def test_token_hashed_and_resolves(harness: Harness) -> None:
    """AC4: only a salted hash is stored; the raw token still resolves to the identity."""
    token = harness.token_for("code_alice", "alice-p")
    stored = list(harness.store.tokens.values())
    assert len(stored) == 1
    record = stored[0]
    assert token not in json.dumps([r.__dict__ for r in stored])
    assert record.token_hash != token
    assert len(record.token_hash) == 64
    assert record.token_hash == auth.token_hash("token-secret-for-tests", token)
    # A different service secret over the same token gives a different hash (salted, R4).
    assert auth.token_hash("other-secret", token) != record.token_hash
    identity_record = harness.store.identities[record.identity_id]
    assert identity_record.pseudonym == "alice-p"


def test_github_token_discarded(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    """AC5: the GitHub access token is never stored and never logged."""
    with caplog.at_level(logging.DEBUG):
        harness.token_for("code_alice", "alice-p")
    dumped = json.dumps(
        {
            "identities": [i.__dict__ for i in harness.store.identities.values()],
            "tokens": [t.__dict__ for t in harness.store.tokens.values()],
            "claims": [],
            "ephemeral": {k: str(v) for k, v in harness.store.ephemeral.items()},
        }
    )
    assert FAKE_ACCESS_TOKEN not in dumped
    assert FAKE_ACCESS_TOKEN not in caplog.text
    # The identity keeps only what §7 allows: pseudonym, proof kind, login, created.
    stored = next(iter(harness.store.identities.values()))
    assert set(stored.__dict__) == {"id", "pseudonym", "proof_kind", "proof_reference", "created"}


def test_state_is_single_use_and_expires(harness: Harness) -> None:
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    first = harness.client.get(
        "/auth/github/callback",
        params={"code": "code_alice", "state": state},
        headers={"Accept": "application/json"},
    )
    assert first.status_code == 200
    second = harness.client.get(
        "/auth/github/callback", params={"code": "code_alice", "state": state}
    )
    assert second.status_code == 400
    assert second.json()["error"] == "state-invalid"

    other = harness.client.get("/auth/github/start", follow_redirects=False)
    state2 = other.headers["location"].split("state=")[1].split("&")[0]
    harness.clock.advance(seconds=601)
    expired = harness.client.get(
        "/auth/github/callback", params={"code": "code_alice", "state": state2}
    )
    assert expired.status_code == 400
    assert expired.json()["error"] == "state-invalid"


def test_unknown_code_is_502(harness: Harness) -> None:
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    r = harness.client.get("/auth/github/callback", params={"code": "nope", "state": state})
    assert r.status_code == 502
    assert r.json()["error"] == "github-exchange-failed"


def test_one_token_per_github_login(harness: Harness) -> None:
    """R6: the invited-run default is one identity per GitHub login."""
    harness.token_for("code_alice", "alice-p")
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    r = harness.client.get("/auth/github/callback", params={"code": "code_alice", "state": state})
    assert r.status_code == 409
    assert r.json()["error"] == "github-login-taken"


def test_browser_flow_serves_escaped_html() -> None:
    """The human path (Q4): a form, then the token page; both escape what GitHub returned."""
    h = make_harness()
    h.githost.users["code_x"] = alice().__class__(
        login="<script>alert(1)</script>", id=9, created_at="2020-01-01T00:00:00Z"
    )
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    page = h.client.get("/auth/github/callback", params={"code": "code_x", "state": state})
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text
    assert 'action="/tokens"' in page.text.replace("'", '"')
