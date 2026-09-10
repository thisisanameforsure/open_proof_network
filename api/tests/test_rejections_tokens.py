"""Token issuance refusals not yet named by a test (F05-R3, R4, R6; F06-R7, Q9)."""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness, PrecheckKey, make_harness, make_precheck_key

from opn_api import identity

DCO = {"version": identity.DCO_VERSION, "accepted": True}


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def callback(h: Harness, code: str = "code_alice") -> dict[str, Any]:
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    r = h.client.get(
        "/auth/github/callback",
        params={"code": code, "state": state},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def mint(h: Harness, proof: Any, pseudonym: str = "alice-p", **body: Any) -> Any:
    return h.client.post(
        "/tokens", json={"proof": proof, "pseudonym": pseudonym, "dco": DCO, **body}
    )


def test_callback_without_code_or_state_is_400(harness: Harness) -> None:
    """R3: GitHub's callback must carry both; neither half alone reaches the exchange."""
    for params in ({"code": "code_alice"}, {"state": "x"}, {}):
        r = harness.client.get("/auth/github/callback", params=params)
        assert r.status_code == 400, params
        assert r.json()["error"] == "callback-incomplete"
    assert harness.githost.exchanges == []


def test_forged_state_never_reaches_the_exchange(harness: Harness) -> None:
    """A state the service did not mint is refused before any call to GitHub is made."""
    r = harness.client.get(
        "/auth/github/callback", params={"code": "code_alice", "state": "forged-state"}
    )
    assert r.status_code == 400
    assert r.json()["error"] == "state-invalid"
    assert harness.githost.exchanges == []


def test_github_proof_expires_with_the_state_ttl(harness: Harness) -> None:
    """§7: a proof outlives the callback by ``state_ttl_s`` and not a second more."""
    proof = callback(harness)["proof"]
    harness.clock.advance(seconds=harness.settings.state_ttl_s + 1)
    r = mint(harness, proof)
    assert r.status_code == 400
    assert r.json()["error"] == "proof-invalid"
    assert harness.store.identities == {}


@pytest.mark.parametrize(
    "proof",
    [None, "github", 7, [], {}, {"kind": None}, {"id": "abc"}],
)
def test_proof_that_is_not_a_kinded_object_is_unsupported(harness: Harness, proof: Any) -> None:
    r = mint(harness, proof)
    assert r.status_code == 400, proof
    assert r.json()["error"] == "proof-unsupported", proof


def test_github_proof_with_a_non_string_or_empty_id_is_invalid(harness: Harness) -> None:
    for bad in ({"kind": "github"}, {"kind": "github", "id": 7}, {"kind": "github", "id": ""}):
        r = mint(harness, bad)
        assert r.status_code == 400, bad
        assert r.json()["error"] == "proof-invalid", bad


def test_dco_acceptance_must_be_the_boolean_true(harness: Harness) -> None:
    """R4: ``"true"``, ``1`` and ``"yes"`` are not acceptance in a JSON body; only ``true``."""
    proof = callback(harness)["proof"]
    for accepted in ("true", 1, "yes", "on"):
        r = mint(harness, proof, dco={"version": identity.DCO_VERSION, "accepted": accepted})
        assert r.status_code == 400, accepted
        assert r.json()["error"] == "dco-not-accepted", accepted
    assert harness.store.identities == {}
    # The refusals above spent nothing: the proof still mints.
    assert mint(harness, proof).status_code == 201


def test_dco_that_is_not_an_object_is_not_accepted(harness: Harness) -> None:
    proof = callback(harness)["proof"]
    for dco in (True, "accepted", [identity.DCO_VERSION]):
        r = mint(harness, proof, dco=dco)
        assert r.status_code == 400, dco
        assert r.json()["error"] == "dco-not-accepted", dco


def test_two_live_proofs_for_one_login_mint_one_identity(harness: Harness) -> None:
    """R6's one-token-per-login rule holds under a race: two callbacks for alice both succeed
    (no identity exists yet), the first mint wins, the second is refused by the store's
    proof-reference uniqueness rather than by the callback's count."""
    first = callback(harness)["proof"]
    second = callback(harness)["proof"]
    assert mint(harness, first, "alice-one").status_code == 201
    r = mint(harness, second, "alice-two")
    assert r.status_code == 409
    assert r.json()["error"] == "github-login-taken"
    assert [i.pseudonym for i in harness.store.identities.values()] == ["alice-one"]
    assert len(harness.store.tokens) == 1


def test_tutorial_exchange_is_address_limited_like_a_token_start(key: PrecheckKey) -> None:
    """F06-Q9: the exchange shares the token-start counter, so an address that has used its
    starts for the day cannot mint through the tutorial path either — and the nonce survives
    the 429 for tomorrow."""
    h = make_harness({"OPN_API_TOKEN_STARTS_PER_DAY": "1"})
    job = h.tutorial_job(key)
    assert h.client.get("/auth/github/start", follow_redirects=False).status_code == 302
    proof = {"kind": "tutorial", "job_id": job["id"], "nonce": job["nonce"]}
    r = mint(h, proof, "anon-p")
    assert r.status_code == 429
    assert r.json()["error"] == "rate-limited"
    assert int(r.headers["retry-after"]) > 0
    assert h.store.identities == {}

    h.clock.advance(days=1)
    assert mint(h, proof, "anon-p").status_code == 201


def test_tutorial_proof_with_non_string_fields_is_the_same_400(harness: Harness) -> None:
    """R7: no probe distinguishes a malformed proof from a wrong one."""
    for proof in (
        {"kind": "tutorial"},
        {"kind": "tutorial", "job_id": 7, "nonce": 8},
        {"kind": "tutorial", "job_id": ["x"], "nonce": None},
    ):
        r = mint(harness, proof, "anon-p")
        assert r.status_code == 400, proof
        assert r.json()["error"] == "proof-invalid", proof


def test_bad_pseudonym_is_refused_before_the_proof_is_spent(harness: Harness) -> None:
    """Order matters for a stranger: a bad pseudonym is refused before the proof is looked at,
    so a bad request does not burn a proof that was valid."""
    proof = callback(harness)["proof"]
    assert mint(harness, proof, "not a pseudonym").status_code == 400
    assert mint(harness, proof, "alice-p").status_code == 201
