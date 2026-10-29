"""Testers 2026-10-27 (erdos-849), D's F-D2: a GitHub-only route asks who is asking first.

The story. With a tutorial token, ``POST /reviews/erdos-849/answers`` answered ``400
unknown-field`` ("this route accepts answer, cites, question") for a body with an extra field and
``403 github-login-required`` for a well-formed one: the same identity got two refusals depending
on the body, and learned the body grammar of a route it can never use.

The mechanism. Each route read ``identitymod.body_fields`` before ``stewards.github_login``. The
login check reads only the identity, so it now comes first, before the body and before any
lookup the body or path drives: an identity with no GitHub login gets ``403
github-login-required`` whatever it sends.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api_fakes import Harness, make_harness
from test_web_session import ENV, web_headers

from opn_api import auth, identity
from opn_api.store import Identity

#: Every route that writes as a GitHub login (``stewards.github_login``).
GITHUB_ONLY = (
    "/stewards",
    "/approvals",
    "/motions",
    "/votes",
    "/writeups",
    "/literature/confirm",
    "/registrations",
    "/shelvings",
    "/reviews",
    "/reviews/erdos-849/answers",
    "/reviews/erdos-849/signatures",
)


@pytest.fixture
def h() -> Iterator[Harness]:
    harness = make_harness(ENV)
    with harness.client:
        yield harness


def tutorial_session(h: Harness) -> str:
    held = Identity(
        "01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z", identity.DCO_VERSION
    )
    h.store.put_identity(held)
    raw, _ = auth.new_session(h.context, held.id)
    return raw


@pytest.mark.parametrize("route", GITHUB_ONLY)
@pytest.mark.parametrize("body", [{"not_a_field": 1}, {}], ids=["unknown-field", "empty"])
def test_a_tutorial_identity_is_refused_for_who_it_is_not_what_it_sent(
    h: Harness, route: str, body: dict[str, object]
) -> None:
    r = h.client.post(route, json=body, headers=web_headers(tutorial_session(h)))
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "github-login-required"
    assert h.githost.pushes == [] and h.githost.pulls == []
