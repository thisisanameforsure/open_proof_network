"""Rejections at the application boundary (F05-R1, R5, R11, R13; C7, C8; conventions §4, §5).

What every route shares: the body parser, the bearer gate, the write limit, the R13 gate, and the
two catch-all handlers. Each test here names the failing case it proves and asserts on the
response the caller sees — a malformed body is a named 400, a store that explodes is a 500 that
says nothing about why, and no token or secret ever travels back out in a body or a log.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pytest
from api_fakes import TEST_ENV, FakeClock, FakeGitHost, Harness, make_harness
from starlette.testclient import TestClient

from opn_api import auth, config, identity
from opn_api.app import create_app
from opn_api.store import Claim, MemoryStore, TokenRecord

CLAIM = {"node_id": "and-reassoc"}
SECRETS = ("token-secret-for-tests", "client-secret-for-tests", "-----BEGIN TEST KEY-----")


# --- the body parser (identity.body_fields) -------------------------------------------------------


def test_malformed_json_body_is_a_named_400(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/claims",
        content=b'{"node_id": "and-reassoc"',  # unterminated
        headers={**harness.auth(token), "Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "malformed-body"
    assert harness.store.claims == {}


def test_json_array_body_is_rejected_as_not_an_object(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", json=["and-reassoc"], headers=harness.auth(token))
    assert r.status_code == 400
    assert r.json()["error"] == "malformed-body"
    assert "object" in r.json()["message"]


def test_empty_body_is_missing_fields_not_a_crash(harness: Harness) -> None:
    """An empty body parses as no fields, so the route names the first missing one."""
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", content=b"", headers=harness.auth(token))
    assert r.status_code == 400
    assert r.json()["error"] == "node-id-invalid"
    r = harness.client.post("/tokens", content=b"   \n")
    assert r.status_code == 400
    assert r.json()["error"] == "pseudonym-invalid"


def test_form_body_with_dco_unchecked_is_refused(harness: Harness) -> None:
    """The browser form (Q4) posts urlencoded fields; an unticked box is not acceptance (R4)."""
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    page = harness.client.get(
        "/auth/github/callback", params={"code": "code_alice", "state": state}
    )
    proof_id = page.text.split("name='proof.id' value='")[1].split("'")[0]
    r = harness.client.post(
        "/tokens",
        data={
            "proof.kind": "github",
            "proof.id": proof_id,
            "pseudonym": "alice-p",
            "dco.version": identity.DCO_VERSION,
            "dco.accepted": "off",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"] == "dco-not-accepted"
    assert harness.store.identities == {}


def test_wrong_method_on_a_known_path_is_405(harness: Harness) -> None:
    assert harness.client.get("/claims").status_code == 405
    assert harness.client.put("/tokens", json={}).status_code == 405


# --- the write limit sits behind authentication -------------------------------------------------


def test_rejected_writes_still_consume_the_hourly_budget() -> None:
    """R6 counts write requests, not successful writes: two 400s and the third call is 429."""
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "2"})
    token = h.token_for("code_alice", "alice-p")
    for _ in range(2):
        bad = h.client.post("/claims", json={"node_id": "Not_An_Id"}, headers=h.auth(token))
        assert bad.status_code == 400
    over = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
    assert over.status_code == 429
    assert over.json()["error"] == "rate-limited"


def test_unauthenticated_requests_do_not_consume_an_identity_budget() -> None:
    """The 401 comes before the counter: a stranger hammering a write route cannot exhaust a
    real identity's hour, because there is no identity to charge."""
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "1"})
    token = h.token_for("code_alice", "alice-p")
    for _ in range(3):
        assert h.client.post("/claims", json=CLAIM).status_code == 401
        assert h.client.post("/claims", json=CLAIM, headers=h.auth("garbage")).status_code == 401
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(token)).status_code == 201


# --- C7: a failing store is a visible 500, never a silent success --------------------------------


@dataclass
class ExplodingStore(MemoryStore):
    """A store whose claim write fails the way an unreachable table would."""

    detail: str = "ProvisionedThroughputExceededException: table opn-claims (account 123)"

    def put_claim(self, claim: Claim) -> None:
        raise RuntimeError(self.detail)


def test_store_failure_is_a_500_that_names_nothing(caplog: pytest.LogCaptureFixture) -> None:
    """C7, §5: the caller learns the write failed; the diagnosis goes to the log, not the body."""
    store = ExplodingStore()
    h = make_harness(store=store)
    token = h.token_for("code_alice", "alice-p")
    with caplog.at_level(logging.ERROR, logger="opn_api"):
        r = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
    assert r.status_code == 500
    assert r.json() == {"error": "internal", "message": "internal error"}
    assert store.detail not in r.text
    assert store.claims == {}
    logged = [rec for rec in caplog.records if rec.levelno >= logging.ERROR]
    assert any("RuntimeError" in rec.getMessage() for rec in logged)
    assert any(rec.exc_info for rec in logged), "the traceback must be in the log (§5)"


@dataclass
class UnreachableStore(MemoryStore):
    def check(self) -> list[str]:
        return ["claims table 'opn-claims'"]


def test_store_check_failure_makes_health_503_naming_the_table() -> None:
    """R13: a table the store cannot reach is reported by health and blocks every route."""
    h = make_harness(store=UnreachableStore())
    r = h.client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"ok": False, "missing": ["claims table 'opn-claims'"]}
    blocked = h.client.get("/frontier.json")
    assert blocked.status_code == 503
    assert blocked.json()["error"] == "not-configured"
    assert "opn-claims" in blocked.json()["message"]


def test_health_reports_every_missing_secret_not_just_the_first() -> None:
    """R13: the 503 names *every* missing parameter, so one deploy fixes them all (C7)."""
    env = {
        k: v
        for k, v in TEST_ENV.items()
        if k not in ("OPN_API_TOKEN_SECRET", "OPN_API_GITHUB_PRIVATE_KEY")
    }
    app = create_app(
        config.load(env),
        store=MemoryStore(),
        githost=FakeGitHost.with_fixtures(),
        clock=FakeClock(),
    )
    r = TestClient(app).get("/health")
    assert r.status_code == 503
    assert r.json()["missing"] == ["OPN_API_GITHUB_PRIVATE_KEY", "OPN_API_TOKEN_SECRET"]


# --- C8: nothing secret travels back out ---------------------------------------------------------


def test_no_error_response_or_log_line_carries_the_token_or_a_secret(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """C8, R11: drive every kind of failure a bearer can meet — 400, 401 on a revoked token,
    403, 404, 429, 502 from the host, 500 from the store — and read every body and every log
    record at DEBUG. The token and the three configured secrets appear in none of them."""
    store = ExplodingStore()
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "5"}, store=store)
    token = h.token_for("code_alice", "alice-p")
    other = h.token_for("code_bob", "bob-p")
    h.githost.app_failure = "POST /repos/x/git/refs returned 403: Resource not accessible"
    bodies: list[str] = []
    with caplog.at_level(logging.DEBUG):
        calls = (
            h.client.post("/claims", json={"node_id": "Not_An_Id"}, headers=h.auth(token)),
            h.client.post("/claims", json={"node_id": "no-such-node"}, headers=h.auth(token)),
            h.client.delete("/claims/NOPE", headers=h.auth(token)),
            h.client.post(
                "/annexes", json={"node_id": "and-reassoc", "text": "x"}, headers=h.auth(token)
            ),
            h.client.post("/claims", json=CLAIM, headers=h.auth(token)),  # the store explodes
            h.client.post("/claims", json=CLAIM, headers=h.auth(other)),
        )
        bodies.extend(r.text for r in calls)
        statuses = [r.status_code for r in calls]
        limited = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
        bodies.append(limited.text)
        digest = auth.token_hash("token-secret-for-tests", token)
        record = h.store.tokens[digest]
        h.store.tokens[digest] = TokenRecord(digest, record.identity_id, record.created, True)
        revoked = h.client.post("/claims", json=CLAIM, headers=h.auth(token))
        bodies.append(revoked.text)
    assert statuses == [400, 404, 404, 502, 500, 500]
    assert limited.status_code == 429  # alice's sixth write: the five above used the budget
    assert revoked.status_code == 401
    everything = "\n".join(bodies) + "\n" + caplog.text
    assert token not in everything
    assert other not in everything
    for secret in SECRETS:
        assert secret not in everything, secret
    # The hashed form is the store's business and must not leak either.
    assert digest not in everything


def test_repr_of_the_context_does_not_expose_secrets(harness: Harness) -> None:
    """A Settings repr reaches logs through the app's context; it must show `<set>` only."""
    text = repr(harness.context)
    for secret in SECRETS:
        assert secret not in text, secret
    assert "<set>" in text


def test_anonymous_tutorial_precheck_is_not_charged_to_a_write_budget(harness: Harness) -> None:
    """The precheck route is unauthenticated at the table (F06-Q2), so `check_write` never
    runs for it: an anonymous caller is bounded by the address limit alone, and the identity
    counter stays untouched when a bearer is later presented."""
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "1"})
    body: dict[str, Any] = {
        "node_id": "tutorial-and-swap",
        "bundle": {
            "targets/propositional/nodes/tutorial-and-swap/Proof.lean": (
                "theorem x : True := trivial\n"
            )
        },
    }
    for _ in range(3):
        assert h.client.post("/precheck", json=body).status_code == 202
    token = h.token_for("code_alice", "alice-p")
    assert h.client.post("/claims", json=CLAIM, headers=h.auth(token)).status_code == 201
