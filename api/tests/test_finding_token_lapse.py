"""F05-T27 (audit 2026-10-04; decisions v3.28, D-19): write tokens lapse after ninety days.

D-19 v3.28: "A write token is valid for ninety days from its issue or its last renewal, and its
holder renews it through the service before it lapses; a lapsed token is refused as expired, and
the identity behind it is kept, so a new token for the same identity can be had by the same proof
as the first." Before this task a token never expired: a leaked one was good until the founder
noticed and revoked it.

What the service does now (Q27):
  - a token carries ``expires`` (issue + ``OPN_API_TOKEN_DAYS``, default 90); a token issued
    before this field existed is read as issued at ``OPN_API_TOKEN_CUTOVER``, so it gets a full
    window from the deploy rather than lapsing at once;
  - a lapsed token is 401 ``token-expired`` on every route, and on the MCP the bearer is let
    through to the endpoint so the same refusal comes back rather than "unauthenticated";
  - ``POST /tokens/renew`` (and the ``renew_token`` tool) *rotates*: a fresh token for the same
    identity, a full window, and the presented token retired at once. Extending the same token
    would let whoever copied it renew it for ever beside its holder; rotating bounds a leaked
    token to the window it was copied in, and if the thief renews first the holder's next call
    fails, which is how they find out;
  - a lapsed GitHub identity re-proves with the same login and gets a new token for the same
    identity; a founder-revoked identity does not.

Both stores.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from mcp_client import NODE, McpClient
from test_finding_token_revoke import tokens_tool
from test_store_seam import dynamo

from opn_api import auth, config, identity
from opn_api.mcp.auth import StoreTokenVerifier
from opn_api.store import Identity, MemoryStore, TokenRecord

CLAIM = {"node_id": "and-reassoc"}
DAY = timedelta(days=1)


@pytest.fixture(params=["memory", "dynamodb"])
def harness(request: pytest.FixtureRequest) -> Harness:
    return make_harness(store=MemoryStore() if request.param == "memory" else dynamo())


def write(h: Harness, token: str) -> Any:
    return h.client.post("/claims", json=CLAIM, headers=h.auth(token))


def renew(h: Harness, token: str) -> Any:
    return h.client.post("/tokens/renew", headers=h.auth(token))


def regain(h: Harness, pseudonym: str, code: str = "code_alice") -> Any:
    """The GitHub flow again, for a login that already has an identity."""
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = h.client.get(
        "/auth/github/callback",
        params={"code": code, "state": state},
        headers={"Accept": "application/json"},
    )
    if cb.status_code != 200:
        return cb
    return h.client.post(
        "/tokens",
        json={
            "proof": cb.json()["proof"],
            "pseudonym": pseudonym,
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )


# --- the window ------------------------------------------------------------------------------


def test_a_token_lapses_ninety_days_after_issue(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=89, hours=23)
    assert write(harness, token).status_code == 201
    harness.clock.advance(hours=1)
    refused = write(harness, token)
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"] == "token-expired"
    assert refused.headers["www-authenticate"].startswith("Bearer")
    message = refused.json()["message"]
    assert "2026-12-08" in message  # when it lapsed: issue 2026-09-09 + 90 days
    assert "/auth/github/start" in message  # how to get a new one


def test_the_issue_answer_says_when_the_token_lapses(harness: Harness) -> None:
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = harness.client.get(
        "/auth/github/callback",
        params={"code": "code_alice", "state": state},
        headers={"Accept": "application/json"},
    )
    issued = harness.client.post(
        "/tokens",
        json={
            "proof": cb.json()["proof"],
            "pseudonym": "alice",
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )
    assert issued.status_code == 201
    assert issued.json()["expires"] == "2026-12-08T12:00:00Z"


def test_a_token_from_before_the_field_lapses_ninety_days_after_the_cutover() -> None:
    """A token issued before tokens carried an expiry is read as issued at the cutover: a full
    window from the deploy, never an instant lapse for every live agent."""
    h = make_harness(env={"OPN_API_TOKEN_CUTOVER": "2026-10-10"})
    held = Identity("01LEGACY", "old-hand", "github", "old-hand", "2026-09-01T00:00:00Z")
    h.store.put_identity(held)
    token = auth.new_token()
    h.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(h.settings.token_secret or "", token),
            identity_id=held.id,
            created="2026-09-01T00:00:00Z",
        )
    )
    h.clock.current = datetime(2027, 1, 7, 23, 0, tzinfo=UTC)  # cutover + 89 days 23 h
    assert write(h, token).status_code == 201
    h.clock.current = datetime(2027, 1, 8, 0, 0, 1, tzinfo=UTC)
    assert write(h, token).json()["error"] == "token-expired"


def test_the_window_and_the_cutover_are_configuration() -> None:
    settings = config.load({"OPN_API_TOKEN_DAYS": "30", "OPN_API_TOKEN_CUTOVER": "2026-11-01"})
    assert settings.token_days == 30
    assert settings.token_cutover == "2026-11-01"  # noqa: S105 — a date
    for bad in ({"OPN_API_TOKEN_DAYS": "0"}, {"OPN_API_TOKEN_CUTOVER": "soon"}):
        with pytest.raises(config.ConfigError):
            config.load(bad)


def test_a_shorter_window_lapses_sooner() -> None:
    h = make_harness(env={"OPN_API_TOKEN_DAYS": "7"})
    token = h.token_for("code_alice", "alice")
    h.clock.advance(days=7)
    assert write(h, token).json()["error"] == "token-expired"


# --- the MCP ---------------------------------------------------------------------------------


def test_the_mcp_answers_token_expired_not_unauthenticated(harness: Harness) -> None:
    """A lapsed bearer is let through to the endpoint, which refuses it as expired: the client
    is told to renew or re-prove, not that it never had a token."""
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=91)
    doc = McpClient(harness).failed("claim_node", {"node_id": NODE}, token=token)
    assert doc["status"] == 401
    assert doc["body"]["error"] == "token-expired"
    # An unknown token stays anonymous, as before.
    assert asyncio.run(StoreTokenVerifier(harness.context).verify_token("not-a-token")) is None


# --- renewal ---------------------------------------------------------------------------------


def test_renewal_rotates_the_token_and_resets_the_window(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=80)
    renewed = renew(harness, token)
    assert renewed.status_code == 201, renewed.text
    doc = renewed.json()
    fresh = doc["token"]
    assert fresh != token
    assert doc["identity"]["pseudonym"] == "alice"
    assert doc["expires"] == "2027-02-26T12:00:00Z"  # renewal day 2026-11-28 + 90
    # The presented token is retired at once; the message says why, so a holder who did not
    # renew learns that someone holding their token did.
    old = write(harness, token)
    assert old.status_code == 401
    assert old.json()["error"] == "invalid-token"
    assert "renew" in old.json()["message"]
    harness.clock.advance(days=20)  # 100 days after issue: past the first window
    assert write(harness, fresh).status_code == 201
    harness.clock.advance(days=70)  # 90 days after renewal
    assert write(harness, fresh).json()["error"] == "token-expired"


def test_a_token_renews_once(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    assert renew(harness, token).status_code == 201
    again = renew(harness, token)
    assert again.status_code == 401
    assert again.json()["error"] == "invalid-token"


def test_a_lapsed_token_cannot_renew(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.clock.advance(days=90)
    refused = renew(harness, token)
    assert refused.status_code == 401
    assert refused.json()["error"] == "token-expired"


def test_renewal_needs_a_token_and_takes_no_body(harness: Harness) -> None:
    assert harness.client.post("/tokens/renew").json()["error"] == "unauthenticated"
    token = harness.token_for("code_alice", "alice")
    extra = harness.client.post("/tokens/renew", json={"days": 900}, headers=harness.auth(token))
    assert extra.status_code == 400
    assert extra.json()["error"] == "unknown-field"


def test_the_renew_token_tool_is_the_route(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    client = McpClient(harness)
    doc = client.ok("renew_token", {}, token=token)
    assert doc["status"] == 201
    fresh = doc["body"]["token"]
    assert write(harness, fresh).status_code == 201
    assert write(harness, token).status_code == 401


def test_the_revoke_tool_still_stops_a_renewed_token(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    fresh = renew(harness, token).json()["token"]
    identity_, count = tokens_tool().revoke(harness.store, "alice")
    assert identity_ is not None and count == 1  # the retired one was already retired
    assert write(harness, fresh).json()["error"] == "invalid-token"


# --- a new token by the same proof -----------------------------------------------------------


def test_a_lapsed_github_identity_gets_a_new_token_by_the_same_login(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    first = harness.store.get_identity_by_pseudonym("alice")
    assert first is not None
    harness.clock.advance(days=91)
    again = regain(harness, "alice")
    assert again.status_code == 201, again.text
    assert again.json()["identity"]["id"] == first.id  # the same identity, kept
    assert write(harness, again.json()["token"]).status_code == 201
    assert write(harness, token).json()["error"] == "token-expired"


def test_the_same_login_must_name_its_own_pseudonym(harness: Harness) -> None:
    harness.token_for("code_alice", "alice")
    harness.clock.advance(days=91)
    other = regain(harness, "someone-new")
    assert other.status_code == 409
    assert other.json()["error"] == "github-login-taken"
    assert "alice" in other.json()["message"]


def test_a_live_token_is_not_replaced_by_signing_in_again(harness: Harness) -> None:
    """Before a lapse the way to a new token is renewal; the login refuses as it always did."""
    harness.token_for("code_alice", "alice")
    refused = regain(harness, "alice")
    assert refused.status_code == 409
    assert refused.json()["error"] == "github-login-taken"


def test_a_revoked_identity_does_not_come_back_by_signing_in(harness: Harness) -> None:
    """Revocation stops the credential (F05-T21); a lapse after it must not undo it."""
    harness.token_for("code_alice", "alice")
    tokens_tool().revoke(harness.store, "alice")
    harness.clock.advance(days=91)
    refused = regain(harness, "alice")
    assert refused.status_code == 409
    assert refused.json()["error"] == "github-login-taken"


def test_a_lapsed_identity_with_a_reserved_name_keeps_it(harness: Harness) -> None:
    """Reservation governs new identities (F05-T26): re-proving an existing one is not new."""
    held = Identity("01ADMIN", "admin", "github", "alice", "2026-09-01T00:00:00Z")
    harness.store.put_identity(held)
    harness.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(harness.settings.token_secret or "", auth.new_token()),
            identity_id=held.id,
            created="2026-09-01T00:00:00Z",
            expires="2026-09-02T00:00:00Z",
        )
    )
    again = regain(harness, "admin")
    assert again.status_code == 201, again.text
    assert again.json()["identity"]["id"] == "01ADMIN"
