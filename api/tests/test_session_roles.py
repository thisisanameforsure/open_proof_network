"""F23-T4 / AC4: ``GET /session`` and ``POST /session/end`` (R4).

The roles are read from the graph at the service's current commit: ``curators.json`` for a
curator, and ``targets/*/stewards/*.yaml`` (``steward/v1`` and ``steward/v2``) for the targets a
login is an active steward of, the latest record per login deciding. The fixture graph is
``test_glosses_route``'s: the owner listed as curator, ``alice`` an SSH-signed steward.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, TARGET, make_keys, make_tree, serve
from test_web_session import ENV, SITE, sign_in, web_headers

from opn_api.githost import GitHubUser
from opn_gate import steward

DUMMY_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA== approval"
DUMMY_SIG = "-----BEGIN SSH SIGNATURE-----\nU1NIU0lH\n-----END SSH SIGNATURE-----\n"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


def harness_over(tree: Path) -> Iterator[Harness]:
    h = make_harness(ENV)
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    serve(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness_over(tree)


def session(h: Harness, cookie: str | None) -> Any:
    headers = web_headers(cookie) if cookie else {"Origin": SITE, "X-OPN-Web": "1"}
    return h.client.get("/session", headers=headers)


def v2_record(login: str, action: str, n: int, root: Path) -> None:
    """A ``steward/v2`` record written straight into the tree (the signature is the gate's to
    check, so a placeholder serves here)."""
    doc = {
        "schema": "steward/v2",
        "target": TARGET,
        "action": action,
        "login": login,
        "name": login.title(),
        "link": None,
        "commitment": steward.SENTENCE_FOR[action],
        "date": "2026-10-07",
        "via": "approval-key",
        "admitted_by": "self",
        "key": DUMMY_KEY,
        "signature": DUMMY_SIG,
    }
    path = root / "targets" / TARGET / "stewards" / f"{n}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_signed_out_answers_signed_in_false(h: Harness) -> None:
    r = session(h, None)
    assert r.status_code == 200
    assert r.json() == {"signed_in": False}
    assert r.headers["access-control-allow-origin"] == SITE
    assert r.headers["access-control-allow-credentials"] == "true"


def test_a_steward_session_answers_its_roles_exactly(h: Harness) -> None:
    """AC4: alice is an active steward of the target and no curator."""
    cookie = sign_in(h, "code_alice")
    r = session(h, cookie)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert set(doc) == {
        "signed_in", "login", "pseudonym", "curator", "stewards", "expires",
        "awaiting",  # F24-T5: what waits for the login's vote or acceptance
    }  # fmt: skip
    assert doc["awaiting"] == {"votes": [], "invitations": []}
    assert doc["signed_in"] is True
    assert doc["login"] == "alice" and doc["pseudonym"] == "alice"
    assert doc["curator"] is False
    assert doc["stewards"] == [TARGET]
    assert doc["expires"] == "2026-09-09T20:00:00Z"  # the fake clock plus eight hours


def test_the_owner_is_a_curator_and_no_steward(h: Harness) -> None:
    """AC4: the owner, listed in curators.json, signs in under the fallback pseudonym (his login
    is reserved) and is still recognised by login."""
    doc = session(h, sign_in(h, "code_owner")).json()
    assert doc["login"] == CURATOR
    assert doc["pseudonym"] == CURATOR + "-gh"
    assert doc["curator"] is True
    assert doc["stewards"] == []


def test_a_stranger_has_no_role(h: Harness) -> None:
    doc = session(h, sign_in(h, "code_carol")).json()
    assert (doc["curator"], doc["stewards"]) == (False, [])


def test_a_v2_step_down_ends_a_v1_commitment_and_a_v2_commit_counts(tree: Path) -> None:
    """R4: v1 and v2 are both read, the latest record per login deciding."""
    v2_record("alice", steward.STEP_DOWN, 2, tree)
    v2_record("carol", steward.COMMIT, 3, tree)
    for h in harness_over(tree):
        assert session(h, sign_in(h, "code_alice")).json()["stewards"] == []
        assert session(h, sign_in(h, "code_carol")).json()["stewards"] == [TARGET]


def test_a_session_that_ended_answers_signed_in_false(h: Harness) -> None:
    cookie = sign_in(h, "code_alice")
    h.clock.advance(hours=8, seconds=1)
    assert session(h, cookie).json() == {"signed_in": False}


def test_session_needs_the_sites_origin_and_header(h: Harness) -> None:
    """R3: without the site's Origin and the header, the cookie is not read."""
    cookie = sign_in(h, "code_alice")
    r = h.client.get("/session", headers={"Cookie": f"opn_session={cookie}"})
    assert r.json() == {"signed_in": False}


def test_end_clears_the_cookie_and_the_session(h: Harness) -> None:
    cookie = sign_in(h, "code_alice")
    r = h.client.post("/session/end", headers=web_headers(cookie))
    assert r.status_code == 204
    set_cookie = r.headers["set-cookie"].lower()
    assert set_cookie.startswith("opn_session=;") and "max-age=0" in set_cookie
    assert r.headers["access-control-allow-origin"] == SITE
    assert session(h, cookie).json() == {"signed_in": False}


def test_end_without_a_session_is_still_204(h: Harness) -> None:
    r = h.client.post("/session/end", headers={"Origin": SITE, "X-OPN-Web": "1"})
    assert r.status_code == 204


def test_session_routes_answer_a_preflight(h: Harness) -> None:
    for path in ("/session", "/session/end"):
        r = h.client.options(path, headers={"Origin": SITE, "Access-Control-Request-Method": "GET"})
        assert r.status_code == 204, path
        assert r.headers["access-control-allow-credentials"] == "true"
