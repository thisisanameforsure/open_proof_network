"""F25-T3 / AC16: the DCO names both licences, and a token issued against the older text is asked
to accept again (F25-R16; D-23 v3.37).

The Linux Foundation's text is verbatim and unchanged; the network's addition sits after it,
marked as the network's, and names Apache-2.0 for code and CDLA-Permissive-2.0 for the record by
their SPDX identifiers. ``DCO_VERSION`` is the hash of the text, so it changed by itself; the
version the service published before this text is pinned here so the refusal is tested against
the real predecessor rather than a made-up string.
"""

from __future__ import annotations

import hashlib

from api_fakes import Harness

from opn_api import identity

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
    assert identity.DCO_VERSION == hashlib.sha256(identity.DCO_TEXT.encode()).hexdigest()[:16]
    assert identity.DCO_VERSION != PREVIOUS_VERSION


def test_dco_json_serves_the_new_version_and_text(harness: Harness) -> None:
    r = harness.client.get("/dco.json")
    assert r.status_code == 200, r.text
    assert r.json() == {"version": identity.DCO_VERSION, "text": identity.DCO_TEXT}
    assert "CDLA-Permissive-2.0" in r.json()["text"]


def issue(h: Harness, version: str) -> tuple[int, dict[str, object]]:
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
