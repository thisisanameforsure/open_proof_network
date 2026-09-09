"""F05-T2: bearer authentication (R5; AC6)."""

from __future__ import annotations

from api_fakes import Harness

from opn_api import auth
from opn_api.store import TokenRecord

CLAIM = {"node_id": "and-reassoc"}


def test_bearer_required(harness: Harness) -> None:
    """AC6: no bearer -> 401; unknown or revoked token -> 401."""
    none = harness.client.post("/claims", json=CLAIM)
    assert none.status_code == 401
    assert none.json()["error"] == "unauthenticated"
    assert none.headers["www-authenticate"] == "Bearer"

    unknown = harness.client.post("/claims", json=CLAIM, headers=harness.auth("not-a-token"))
    assert unknown.status_code == 401
    assert unknown.json()["error"] == "invalid-token"

    token = harness.token_for("code_alice", "alice-p")
    ok = harness.client.post("/claims", json=CLAIM, headers=harness.auth(token))
    assert ok.status_code == 201, ok.text

    digest = auth.token_hash("token-secret-for-tests", token)
    record = harness.store.tokens[digest]
    harness.store.tokens[digest] = TokenRecord(
        token_hash=record.token_hash,
        identity_id=record.identity_id,
        created=record.created,
        revoked=True,
    )
    revoked = harness.client.post("/claims", json=CLAIM, headers=harness.auth(token))
    assert revoked.status_code == 401
    assert revoked.json()["error"] == "invalid-token"


def test_malformed_authorization_header(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    for header in [token, f"Basic {token}", "Bearer", "Bearer   "]:
        r = harness.client.post("/claims", json=CLAIM, headers={"Authorization": header})
        assert r.status_code == 401, header
        assert r.json()["error"] == "unauthenticated", header


def test_token_of_deleted_identity_is_401(harness: Harness) -> None:
    """C7: a token whose identity vanished authenticates nobody."""
    token = harness.token_for("code_alice", "alice-p")
    harness.store.identities.clear()
    r = harness.client.post("/claims", json=CLAIM, headers=harness.auth(token))
    assert r.status_code == 401


def test_new_tokens_are_unique_and_urlsafe() -> None:
    tokens = {auth.new_token() for _ in range(200)}
    assert len(tokens) == 200
    assert all(
        t.strip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_") == ""
        for t in tokens
    )
