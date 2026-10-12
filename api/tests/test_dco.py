"""F25-T3 / AC16: the DCO names both licences, and a token issued against the older text is asked
to accept again (F25-R16; D-23 v3.37) — at issuance, and, since the owner's ruling on Q24
(2026-10-11), on every write a live token makes until it has accepted the current text through
``POST /dco/accept``.

The Linux Foundation's text is verbatim and unchanged; the network's addition sits after it,
marked as the network's, and names Apache-2.0 for code and CDLA-Permissive-2.0 for the record by
their SPDX identifiers. ``DCO_VERSION`` is the hash of the text, so it changed by itself; the
version the service published before this text is pinned here so the refusal is tested against
the real predecessor rather than a made-up string.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from api_fakes import Harness
from test_store_seam import dynamo

from opn_api import identity, routes
from opn_api.store import Identity, MemoryStore, Store
from opn_gate import codes

#: ``identity.DCO_VERSION`` as the service published it before F25-T3 (measured 2026-10-11).
PREVIOUS_VERSION = "f7ac75b443f4ca16"

LF_TEXT_START = "Developer Certificate of Origin\nVersion 1.1\n"
LF_CLAUSE_D = "(d) I understand and agree that this project and the contribution"


def test_the_text_names_both_spdx_identifiers() -> None:
    assert "Apache-2.0" in identity.DCO_TEXT
    assert "CDLA-Permissive-2.0" in identity.DCO_TEXT
    # code is Apache, the record is CDLA: each identifier sits in the sentence about its subject
    code_sentence = identity.DCO_TEXT[identity.DCO_TEXT.index("Code contributions") :]
    assert code_sentence.index("Apache-2.0") < code_sentence.index("CDLA-Permissive-2.0")
    assert "non-code record" in identity.DCO_TEXT
    for record in ("attestations", "postmortems", "approach records", "registration records"):
        assert record in identity.DCO_TEXT, record


def test_the_linux_foundation_text_is_verbatim_and_the_addition_is_marked() -> None:
    assert identity.DCO_TEXT.startswith(LF_TEXT_START)
    addition_at = identity.DCO_TEXT.index("Open Proof Network's addition")
    assert identity.DCO_TEXT.index(LF_CLAUSE_D) < addition_at
    assert "not part of the Developer's\nCertificate of Origin" in identity.DCO_TEXT
    # nothing of the network's sits inside the Foundation's clauses
    foundation = identity.DCO_TEXT[:addition_at]
    assert "Apache" not in foundation and "CDLA" not in foundation


def test_the_version_is_the_hash_of_the_text_and_has_changed() -> None:
    expected = hashlib.sha256(identity.DCO_TEXT.encode()).hexdigest()[:16]
    assert expected == identity.DCO_VERSION
    assert identity.DCO_VERSION != PREVIOUS_VERSION


def test_dco_json_serves_the_new_version_and_text(harness: Harness) -> None:
    r = harness.client.get("/dco.json")
    assert r.status_code == 200, r.text
    assert r.json() == {"version": identity.DCO_VERSION, "text": identity.DCO_TEXT}
    assert "CDLA-Permissive-2.0" in r.json()["text"]


def issue(h: Harness, version: str) -> tuple[int, dict[str, Any]]:
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = h.client.get(
        "/auth/github/callback",
        params={"code": "code_alice", "state": state},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 200, cb.text
    r = h.client.post(
        "/tokens",
        json={
            "proof": cb.json()["proof"],
            "pseudonym": "alice",
            "dco": {"version": version, "accepted": True},
        },
    )
    return r.status_code, r.json()


def test_a_token_request_naming_the_previous_version_is_refused_stale(harness: Harness) -> None:
    status, body = issue(harness, PREVIOUS_VERSION)
    assert status == 400, body
    assert body["error"] == "dco-version-stale"
    assert identity.DCO_VERSION in str(body["message"])
    assert "/dco.json" in str(body["message"])
    # the same proof, re-accepted at the current version, is issued a token
    status, body = issue(harness, identity.DCO_VERSION)
    assert status == 201, body
    assert body["identity"]["pseudonym"] == "alice"


# --- F25-R16 (Q24, the owner's ruling of 2026-10-11): live tokens accept the new text too --------


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def age_acceptance(h: Harness, pseudonym: str, version: str | None) -> None:
    """Make the service's record say the identity accepted ``version`` (or, with ``None``, that it
    was created before the version was recorded at all, as every identity on DynamoDB was on the
    day this shipped)."""
    held = h.store.get_identity_by_pseudonym(pseudonym)
    assert held is not None
    h.store.set_dco_version(held.id, version)


def test_a_token_is_issued_with_the_version_it_accepted(harness: Harness) -> None:
    harness.token_for("code_alice", "alice")
    held = harness.store.get_identity_by_pseudonym("alice")
    assert held is not None
    assert held.dco_version == identity.DCO_VERSION


def test_a_live_token_that_accepted_the_previous_text_is_refused_on_writes_only(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    age_acceptance(harness, "alice", PREVIOUS_VERSION)
    # a write: refused before the body is read (an empty body would be a 400 otherwise)
    r = harness.client.post("/claims", json={}, headers=bearer(token))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "dco-reaccept-required"
    assert "/dco.json" in r.json()["message"] and "/dco/accept" in r.json()["message"]
    # the renewal is a write too: a token cannot outlive the text it accepted by renewing
    r = harness.client.post("/tokens/renew", json={}, headers=bearer(token))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "dco-reaccept-required"
    # the identity's own reads are untouched: the bearer still names who is asking
    r = harness.client.get("/claims/mine", headers=bearer(token))
    assert r.status_code == 200, r.text


def test_an_identity_with_no_recorded_acceptance_is_refused_too(harness: Harness) -> None:
    """Every identity that existed before this shipped has no version on its record; it is
    asked to accept, not waved through."""
    token = harness.token_for("code_alice", "alice")
    age_acceptance(harness, "alice", None)
    r = harness.client.post("/claims", json={}, headers=bearer(token))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "dco-reaccept-required"


def test_accepting_the_current_text_lifts_the_refusal(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    age_acceptance(harness, "alice", PREVIOUS_VERSION)
    # the previous version again is stale, as it is on POST /tokens
    r = harness.client.post(
        "/dco/accept",
        json={"dco": {"version": PREVIOUS_VERSION, "accepted": True}},
        headers=bearer(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "dco-version-stale"
    # not ticked
    r = harness.client.post(
        "/dco/accept",
        json={"dco": {"version": identity.DCO_VERSION, "accepted": False}},
        headers=bearer(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "dco-not-accepted"
    # the current one, accepted
    r = harness.client.post(
        "/dco/accept",
        json={"dco": {"version": identity.DCO_VERSION, "accepted": True}},
        headers=bearer(token),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {
        "identity": {"pseudonym": "alice"},
        "dco": {"version": identity.DCO_VERSION, "accepted": True},
    }
    held = harness.store.get_identity_by_pseudonym("alice")
    assert held is not None and held.dco_version == identity.DCO_VERSION
    # and the write is judged on its own terms again
    r = harness.client.post("/claims", json={}, headers=bearer(token))
    assert r.status_code == 400, r.text
    assert r.json()["error"] != "dco-reaccept-required"


def test_the_accept_route_needs_a_bearer_and_takes_only_the_dco(harness: Harness) -> None:
    r = harness.client.post("/dco/accept", json={"dco": {"version": "x", "accepted": True}})
    assert r.status_code == 401, r.text
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/dco/accept",
        json={"dco": {"version": identity.DCO_VERSION, "accepted": True}, "pseudonym": "bob"},
        headers=bearer(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "unknown-field"


def test_re_proving_an_identity_records_the_acceptance_again(harness: Harness) -> None:
    """A lapsed GitHub identity that regains a token (F05-T29) accepts the text in that request,
    so the acceptance is recorded for the existing identity, not only for a new one. (A live
    identity cannot regain one — ``github-login-taken`` — so its path is POST /dco/accept.)"""
    harness.token_for("code_alice", "alice")
    age_acceptance(harness, "alice", PREVIOUS_VERSION)
    harness.clock.advance(days=181)  # the idle window: the token lapses, the identity remains
    token = harness.token_for("code_alice", "alice")
    held = harness.store.get_identity_by_pseudonym("alice")
    assert held is not None and held.dco_version == identity.DCO_VERSION
    r = harness.client.post("/claims", json={}, headers=bearer(token))
    assert r.status_code == 400, r.text  # the body, not the sign-off, is what is wrong now


def test_the_route_is_in_the_index_the_catalog_and_the_decisions(harness: Harness) -> None:
    assert "POST /dco/accept" in routes.PURPOSES
    assert "dco-reaccept-required" in codes.CATALOG
    spec = next(r for r in routes.ROUTES if r.label == "POST /dco/accept")
    assert spec.authenticated and spec.write and spec.d35 == "POST /dco/accept"
    r = harness.client.get("/errors.json", params={"prefix": "dco-"})
    assert {row["code"] for row in r.json()["codes"]} >= {"dco-reaccept-required"}


# --- the store seam: both halves record the acceptance the same way ------------------------------


@pytest.fixture(params=["memory", "dynamodb"])
def store(request: pytest.FixtureRequest) -> Store:
    return MemoryStore() if request.param == "memory" else dynamo()


def test_the_acceptance_round_trips_in_both_stores(store: Store) -> None:
    held = Identity(
        id="01IDENTITY00000000000000000",
        pseudonym="alice",
        proof_kind="github",
        proof_reference="alice",
        created="2026-10-11T12:00:00Z",
    )
    assert held.dco_version is None  # the field's default is "never recorded"
    store.put_identity(held)
    got = store.get_identity(held.id)
    assert got is not None and got.dco_version is None
    store.set_dco_version(held.id, identity.DCO_VERSION)
    got = store.get_identity(held.id)
    assert got is not None and got.dco_version == identity.DCO_VERSION
    assert store.get_identity_by_pseudonym("alice") == got
    store.set_dco_version(held.id, None)
    got = store.get_identity(held.id)
    assert got is not None and got.dco_version is None
    with pytest.raises(KeyError):
        store.set_dco_version("01NOBODY0000000000000000000", identity.DCO_VERSION)
