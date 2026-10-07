"""F23-T3 / AC1-AC3: GitHub sign-in back to the site, and the web session it leaves (R2, R3).

The session is a cookie on the service's host. httpx keeps no ``Secure`` cookie over the test
client's plain ``http://testserver``, so every request here carries the cookie by hand: what is
under test is what the service sets and what it accepts, not the browser's jar.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness, make_harness

from opn_api import identity

SITE = "https://example.org"
ENV = {"OPN_API_PUBLIC_URL": "https://api.example.org"}  # the site origin follows (F22-T8)
RETURN = "/problems/erdos-1094/"
COOKIE = "opn_session"


@pytest.fixture
def web() -> Any:
    h = make_harness(ENV)
    with h.client:
        yield h


def start(h: Harness, return_path: str | None) -> Any:
    params = {"return": return_path} if return_path is not None else {}
    return h.client.get("/auth/github/start", params=params, follow_redirects=False)


def state_of(response: Any) -> str:
    return str(response.headers["location"].split("state=")[1].split("&")[0])


def callback(h: Harness, code: str, state: str) -> Any:
    return h.client.get(
        "/auth/github/callback", params={"code": code, "state": state}, follow_redirects=False
    )


def cookie_of(response: Any) -> str:
    header = str(response.headers["set-cookie"])
    first = header.split(";")[0]
    name, _, value = first.partition("=")
    assert name == COOKIE, header
    return value


def accept(h: Harness, page: str, *, ticked: bool = True) -> Any:
    proof = page.split("name='proof' value='")[1].split("'", maxsplit=1)[0]
    returned = page.split("name='return' value='")[1].split("'", maxsplit=1)[0]
    form = {"proof": proof, "return": returned, "dco.version": identity.DCO_VERSION}
    if ticked:
        form["dco.accepted"] = "true"
    return h.client.post("/auth/web/accept", data=form, follow_redirects=False)


def sign_in(h: Harness, code: str, return_path: str = RETURN) -> str:
    """The whole web flow, for a login with or without an identity; answers the cookie value."""
    cb = callback(h, code, state_of(start(h, return_path)))
    if cb.status_code == 200:  # a first sign-in: the one DCO tick box
        cb = accept(h, cb.text)
    assert cb.status_code == 303, cb.text
    return cookie_of(cb)


def web_headers(session: str, *, origin: str = SITE, marked: bool = True) -> dict[str, str]:
    headers = {"Cookie": f"{COOKIE}={session}", "Origin": origin}
    if marked:
        headers["X-OPN-Web"] = "1"
    return headers


# --- AC1 ---------------------------------------------------------------------------------------


def test_existing_login_returns_to_the_site_with_a_strict_cookie_and_no_token(web: Harness) -> None:
    """AC1: an identity already exists, so the callback goes straight back to the page."""
    token = web.token_for("code_alice", "alice")
    cb = callback(web, "code_alice", state_of(start(web, RETURN)))
    assert cb.status_code == 303, cb.text
    assert cb.headers["location"] == SITE + RETURN
    attributes = {a.strip().lower() for a in cb.headers["set-cookie"].split(";")[1:]}
    assert {"httponly", "secure", "samesite=strict", "path=/"} <= attributes
    assert any(a.startswith("max-age=") for a in attributes)
    assert token not in cb.text and "token" not in cb.text.lower()


def test_first_sign_in_asks_the_dco_once_and_takes_the_login_as_pseudonym(web: Harness) -> None:
    """AC1, R2: a new login sees one tick box, no pseudonym screen, and no token anywhere."""
    cb = callback(web, "code_bob", state_of(start(web, RETURN)))
    assert cb.status_code == 200
    page = cb.text
    assert "type='checkbox'" in page and "dco.accepted" in page
    assert "name='pseudonym'" not in page
    done = accept(web, page)
    assert done.status_code == 303, done.text
    assert done.headers["location"] == SITE + RETURN
    assert "token" not in done.text.lower()
    held = web.store.get_identity_by_proof(identity.PROOF_GITHUB, "bob")
    assert held is not None and held.pseudonym == "bob"
    assert web.store.list_tokens(held.id) == []  # a web sign-in mints no bearer token


def test_accept_without_the_tick_is_refused_and_creates_nothing(web: Harness) -> None:
    cb = callback(web, "code_bob", state_of(start(web, RETURN)))
    refused = accept(web, cb.text, ticked=False)
    assert refused.status_code == 400
    assert refused.json()["error"] == "dco-not-accepted"
    assert web.store.get_identity_by_proof(identity.PROOF_GITHUB, "bob") is None


@pytest.mark.parametrize(
    "bad",
    [
        "https://evil.example/",
        "//evil.example",
        "/\\evil.example",
        "javascript:alert(1)",
        "problems/x",
        "/" + "a" * 600,
        "/ok\nSet-Cookie: x=y",
    ],
)
def test_return_must_be_a_path_on_the_site(web: Harness, bad: str) -> None:
    """AC1: a URL, a scheme-relative path or anything not a plain path is a 400."""
    r = start(web, bad)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "return-invalid"


def test_without_return_the_flow_is_unchanged(web: Harness) -> None:
    """R2: no ``return``, today's flow: GitHub, then the pseudonym form and a token."""
    r = start(web, None)
    assert r.status_code == 302
    cb = callback(web, "code_alice", state_of(r))
    assert cb.status_code == 200
    assert "name='pseudonym'" in cb.text
    assert "set-cookie" not in cb.headers


def test_a_login_whose_pseudonym_is_reserved_gets_the_fallback() -> None:
    """Q (fallback): a login that cannot be its own pseudonym is ``<login>-gh``."""
    from api_fakes import FakeGitHost  # noqa: PLC0415

    from opn_api.githost import GitHubUser  # noqa: PLC0415

    host = FakeGitHost.with_fixtures(
        code_owner=GitHubUser(login="thisisanameforsure", id=7, created_at="2015-01-01T00:00:00Z")
    )
    h = make_harness(ENV, githost=host)
    with h.client:
        sign_in(h, "code_owner")
        held = h.store.get_identity_by_proof(identity.PROOF_GITHUB, "thisisanameforsure")
        assert held is not None and held.pseudonym == "thisisanameforsure-gh"


# --- AC2 ---------------------------------------------------------------------------------------


GLOSS = {"subject": {"kind": "statement"}, "text": "x"}  # refused for its body, never its caller


def test_cookie_without_the_header_or_from_another_origin_is_refused(web: Harness) -> None:
    session = sign_in(web, "code_alice")
    no_header = web.client.post("/glosses", json=GLOSS, headers=web_headers(session, marked=False))
    assert no_header.status_code == 401
    foreign = web.client.post(
        "/glosses", json=GLOSS, headers=web_headers(session, origin="https://evil.example")
    )
    assert foreign.status_code == 401
    no_origin = web_headers(session)
    del no_origin["Origin"]
    assert web.client.post("/glosses", json=GLOSS, headers=no_origin).status_code == 401


def test_cookie_is_ignored_by_every_other_route(web: Harness) -> None:
    """AC2: a write route outside R3's list never reads the cookie."""
    session = sign_in(web, "code_alice")
    r = web.client.post("/proposals/witness", json={"node_id": "x"}, headers=web_headers(session))
    assert r.status_code == 401
    assert r.json()["error"] == "unauthenticated"


def test_cookie_with_origin_and_header_is_the_logins_identity(web: Harness) -> None:
    """AC2: on ``POST /glosses`` the session is accepted; the request then fails on its body."""
    session = sign_in(web, "code_alice")
    r = web.client.post("/glosses", json=GLOSS, headers=web_headers(session))
    assert r.status_code == 400, r.text
    assert r.headers["access-control-allow-origin"] == SITE
    assert r.headers["access-control-allow-credentials"] == "true"
    assert "origin" in r.headers["vary"].lower()


def test_a_session_ends_after_its_lifetime(web: Harness) -> None:
    session = sign_in(web, "code_alice")
    web.clock.advance(seconds=web.settings.web_session_ttl_s + 1)
    r = web.client.post("/glosses", json=GLOSS, headers=web_headers(session))
    assert r.status_code == 401


def test_a_forged_session_is_refused(web: Harness) -> None:
    sign_in(web, "code_alice")
    r = web.client.post("/glosses", json=GLOSS, headers=web_headers("not-a-session"))
    assert r.status_code == 401


def test_bearer_still_works_on_a_web_route(web: Harness) -> None:
    token = web.token_for("code_alice", "alice")
    r = web.client.post("/glosses", json=GLOSS, headers=web.auth(token))
    assert r.status_code == 400, r.text


def test_preflight_allows_the_site_with_credentials(web: Harness) -> None:
    r = web.client.options(
        "/glosses",
        headers={
            "Origin": SITE,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, x-opn-web",
        },
    )
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == SITE
    assert r.headers["access-control-allow-credentials"] == "true"
    allowed = {h.strip().lower() for h in r.headers["access-control-allow-headers"].split(",")}
    assert {"content-type", "x-opn-web"} <= allowed
    assert "POST" in r.headers["access-control-allow-methods"]


# --- AC3 ---------------------------------------------------------------------------------------


def test_a_bearer_identity_signs_in_as_itself(web: Harness) -> None:
    """AC3: the same identity and pseudonym, and no second identity in the store."""
    web.token_for("code_alice", "alice-proves")
    before = dict(web.store.identities)
    session = sign_in(web, "code_alice")
    assert web.store.identities == before
    held = web.store.get_identity_by_proof(identity.PROOF_GITHUB, "alice")
    assert held is not None and held.pseudonym == "alice-proves"
    r = web.client.post("/glosses", json=GLOSS, headers=web_headers(session))
    assert r.status_code == 400
