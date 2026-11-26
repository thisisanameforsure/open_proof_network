"""F34-T23 (R22; D-19 v3.51 (ii)): the service files the GitHub link an identity is paired with.

* When its holder asks (``POST /me/name`` with ``"github": true``), the record is
  ``display-name/v2`` carrying the login from the service's own record of the pairing — the
  identity's GitHub proof — never a login the caller types. The gate admits what lands.
* An identity not proved through GitHub has no pairing to publish: refused, nothing opened.
* ``github`` is a boolean, and a withdrawal (a null name) carries none.
* Without it, the record is ``display-name/v1`` exactly as before.
* The first web sign-in says, before the tick, that the network will list the person's work
  under their GitHub login.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness
from test_me_name import (
    PSEUDONYM,
    approval,  # noqa: F401 — the approval key fixture
    harness_over,
    keys,  # noqa: F401 — the signing keys fixture
    post,
    tree,  # noqa: F401 — the fixture tree
)

from opn_api import identity
from opn_api.store import Identity
from opn_gate import modes, schemas
from opn_gate.signer import SshKeygenSigner

LOGIN = "alice"  # the fake GitHub's login for code_alice


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:  # noqa: F811
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


@pytest.fixture
def token(h: Harness) -> str:
    return h.token_for("code_alice", PSEUDONYM)


def landed_as(h: Harness, tree: Path, response: Any, schema: str) -> tuple[dict[str, Any], str]:  # noqa: F811
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    problems = modes.check_as_service(
        tree, path, push.files[path].encode(), signer=SshKeygenSigner()
    )
    over = tree.parent / "landed-github"
    over.mkdir(exist_ok=True)
    (over / "doc.yaml").write_text(push.files[path], encoding="utf-8")
    doc = dict(schemas.load_yaml(over / "doc.yaml", schema))
    return doc, "; ".join(d.code for d in problems)


def test_the_holder_asks_and_the_record_carries_the_paired_login(
    h: Harness,
    tree: Path,  # noqa: F811
    token: str,
) -> None:
    held = h.store.get_identity_by_pseudonym(PSEUDONYM)
    assert held is not None and (held.proof_kind, held.proof_reference) == ("github", LOGIN)
    doc, verdict = landed_as(
        h, tree, post(h, token, {"name": "Alice Agent", "github": True}), "display-name/v2"
    )
    assert verdict == "", "the gate admits what the service wrote"
    assert doc["schema"] == "display-name/v2"
    assert (doc["pseudonym"], doc["name"], doc["github"]) == (PSEUDONYM, "Alice Agent", LOGIN)


def test_without_it_the_record_is_v1_as_before(
    h: Harness,
    tree: Path,  # noqa: F811
    token: str,
) -> None:
    for body in ({"name": "Alice Agent"}, {"name": "Alice Agent", "github": False}):
        r = post(h, token, body)
        doc, verdict = landed_as(h, tree, r, "display-name/v1")
        assert verdict == "" and doc["schema"] == "display-name/v1" and "github" not in doc
        h.githost.set_pull_request_state(r.json()["pr_number"], state="closed", merged=False)
        h.context.pulls.clear()
        h.clock.advance(seconds=150)  # past the duplicate guard's two minutes


def test_an_identity_not_proved_through_github_has_nothing_to_publish(h: Harness) -> None:
    held = Identity(
        "01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z", identity.DCO_VERSION
    )
    h.store.put_identity(held)
    raw, record = identity.issue(h.context, held.id, h.clock.now())
    h.store.put_token(record)
    r = post(h, raw, {"name": "The Tutor", "github": True})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "github-not-paired"
    assert h.githost.pushes == []


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name": "Alice Agent", "github": "alice"}, "github"),  # a login is never typed
        ({"name": None, "github": True}, "github"),  # a withdrawal carries no link
    ],
)
def test_github_is_a_flag_and_a_withdrawal_carries_none(
    h: Harness, token: str, body: dict[str, Any], field: str
) -> None:
    r = post(h, token, body)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == field
    assert h.githost.pushes == []


def test_the_first_sign_in_says_the_work_is_listed_under_the_login() -> None:
    page = identity.accept_form(login="grace-h", proof_id="p", path="/me/")
    assert "Contributors page" in page and "under your GitHub login" in page
    assert page.index("under your GitHub login") < page.index("dco.accepted")


def test_the_same_name_with_the_login_is_not_a_duplicate(h: Harness, token: str) -> None:
    """The duplicate guard's fingerprint carries the flag: a name, then the same name with the
    login, are two records (the second is the holder asking)."""
    first = post(h, token, {"name": "Alice Agent"})
    assert first.status_code == 201
    h.githost.set_pull_request_state(first.json()["pr_number"], state="closed", merged=False)
    h.context.pulls.clear()
    second = post(h, token, {"name": "Alice Agent", "github": True})
    assert second.status_code == 201, second.text
