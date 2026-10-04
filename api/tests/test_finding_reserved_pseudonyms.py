"""F05-T26 (audit 2026-10-04; decisions v3.28, D-19): the service reserves pseudonyms.

D-19 v3.28: "A pseudonym may not be one the service reserves — its operator's and the gate's own
names, and the names on a published list of people — compared without regard to case." Before
this task ``check_pseudonym`` held a name to a regular expression only, so anyone could mint an
identity called ``opn-gate`` (the name the post-merge job commits as) or the operator's login, and
the ledger would show work under it.

The reserved set is three sources (``identity.reserved_names``): the operator's logins read from
configuration (the owners of the graph, network and precheck repositories), the App's committer
name without its ``[bot]`` suffix, and the published list ``api/opn_api/reserved_pseudonyms.txt``.
Names are compared after lower-casing and removing ``-`` and ``_``, so ``Opn-Gate`` and ``opngate``
are both ``opn-gate``. An identity that already holds a now-reserved name is not touched. Both
stores.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_store_seam import dynamo

from opn_api import auth, config, identity
from opn_api.store import Identity, MemoryStore, TokenRecord


@pytest.fixture(params=["memory", "dynamodb"])
def harness(request: pytest.FixtureRequest) -> Harness:
    return make_harness(store=MemoryStore() if request.param == "memory" else dynamo())


def mint(h: Harness, pseudonym: str, code: str = "code_alice") -> Any:
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = h.client.get(
        "/auth/github/callback",
        params={"code": code, "state": state},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 200, cb.text
    return h.client.post(
        "/tokens",
        json={
            "proof": cb.json()["proof"],
            "pseudonym": pseudonym,
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )


@pytest.mark.parametrize(
    "name",
    [
        "opn-gate",  # the gate's own name: the post-merge job commits as it
        "Opn-Gate",  # without regard to case
        "opngate",  # and without regard to the separator
        "open-proof-network",  # the App's committer name, less its [bot] suffix
        "thisisanameforsure",  # the operator: the graph repository's owner
        "ThisIsANameForSure",
        "admin",  # the published list
        "Curator",
        "root",
    ],
)
def test_a_reserved_pseudonym_is_refused(harness: Harness, name: str) -> None:
    r = mint(harness, name)
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "pseudonym-reserved"
    assert name in r.json()["message"]


def test_the_proof_survives_a_reserved_name(harness: Harness) -> None:
    """As with a taken name (AC3): the person picks another and the same proof still mints."""
    start = harness.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = harness.client.get(
        "/auth/github/callback",
        params={"code": "code_alice", "state": state},
        headers={"Accept": "application/json"},
    )
    body = {"proof": cb.json()["proof"], "dco": {"version": identity.DCO_VERSION, "accepted": True}}
    refused = harness.client.post("/tokens", json={**body, "pseudonym": "opn-gate"})
    assert refused.status_code == 409
    issued = harness.client.post("/tokens", json={**body, "pseudonym": "alice-p"})
    assert issued.status_code == 201, issued.text


def test_an_ordinary_pseudonym_is_not_reserved(harness: Harness) -> None:
    """Containing a reserved word is not being one: only the whole name is compared."""
    assert mint(harness, "gate-keeper").status_code == 201
    assert mint(harness, "admin-of-nothing", code="code_bob").status_code == 201


def test_the_operator_is_read_from_configuration() -> None:
    """The operator's name comes from the settings, never from a constant in code."""
    settings = config.load(
        {"OPN_API_GRAPH_REPO": "someone-else/graph", "OPN_API_NETWORK_REPO": "someone-else/net"}
    )
    names = identity.reserved_names(settings)
    assert "someoneelse" in names
    assert identity.is_reserved(settings, "Someone-Else")
    assert not identity.is_reserved(settings, "thisisanameforsure-not")


def test_the_published_list_is_a_file_in_the_repository() -> None:
    """The owner adds a name by adding a line; comments and blank lines are not names."""
    listed = identity.published_reserved()
    assert {"admin", "curator", "root", "opngate"} <= listed
    assert all(n and not n.startswith("#") for n in listed)
    assert identity.RESERVED_FILE.is_file()


def test_an_identity_already_holding_a_reserved_name_is_untouched(harness: Harness) -> None:
    """Reservation governs new identities only: one created before a name was reserved keeps its
    name and its token (the owner checks the live table for such names; see the Q entry)."""
    held = Identity("01HOLDER", "Admin", "github", "old-admin", "2026-09-01T00:00:00Z")
    harness.store.put_identity(held)
    token = auth.new_token()
    harness.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(harness.settings.token_secret or "", token),
            identity_id=held.id,
            created=held.created,
        )
    )
    assert identity.is_reserved(harness.settings, "Admin")
    r = harness.client.post("/claims", json={"node_id": "and-reassoc"}, headers=harness.auth(token))
    assert r.status_code == 201, r.text
