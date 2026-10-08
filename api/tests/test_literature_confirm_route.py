"""F23-T12: ``POST /literature/confirm`` (D-3, D-25, D-32 v3.35; the amendment of 2026-10-08 §2).

A steward of the node's target, or a curator, confirms a proposed literature record — or states
the status themselves — from the site (the F23 web session) or with a bearer whose identity is a
GitHub login. The service writes a signed ``literature/v1`` record as that login: ``confirms``
names the proposal (or is null), ``via: approval-key``, ``key`` the approval key's public half
and ``signature`` by the approval key over the canonical body, exactly as ``POST /stewards`` and
``POST /approvals`` sign. What lands is what is tested: the pushed file laid over the graph,
validated against its schema, its signature checked by ``ssh-keygen -Y verify`` and by the
service's own reader. Anyone else is 403; a proposal that is not on the node is 404.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, NODE, NODE_DIR, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import auth, sshsig
from opn_api.githost import GitHubUser
from opn_api.store import Identity
from opn_gate import schemas, signed
from opn_gate.signer import NAMESPACE, SshKeygenSigner

ROUTE = "/literature/confirm"
PROPOSAL = "literature/20261001T090000Z-bob.yaml"
STEWARD = "alice"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    key = tmp_path_factory.mktemp("approval") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "approval"],
        check=True,
    )
    return key.read_text(), key.with_suffix(".pub").read_text().strip()


def proposal_doc() -> dict[str, Any]:
    return {
        "schema": "literature/v1",
        "node": NODE,
        "contributor": "bob",
        "date": "2026-10-01T09:00:00Z",
        "status": "known",
        "references": [
            {"title": "A published proof", "url": "https://example.org/paper", "note": None}
        ],
        "summary": "Proved in the literature; never formalised.",
        "model_and_tooling": None,
        "confirms": None,
        "via": None,
        "key": None,
        "signature": None,
    }


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The propositional fixture (alice a steward, the owner a curator) with bob's proposal
    merged on the node."""
    root = make_tree(tmp_path, keys)
    path = root / NODE_DIR / PROPOSAL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(proposal_doc(), sort_keys=False), encoding="utf-8")
    return root


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    serve_tree(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


def body(**over: Any) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "record": PROPOSAL,
        "status": "known",
        "references": [
            {"title": "A published proof", "url": "https://example.org/paper", "note": "Thm 2."}
        ],
        "summary": "Checked the paper: the statement is its Theorem 2.",
    } | over


def post(h: Harness, cookie: str, doc: dict[str, Any]) -> Any:
    return h.client.post(ROUTE, json=doc, headers=web_headers(cookie))


def landed(h: Harness, tree: Path, response: Any) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    assert list(push.files) == [path]
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    (over / path).parent.mkdir(parents=True, exist_ok=True)
    (over / path).write_text(push.files[path], encoding="utf-8")
    return dict(schemas.load_yaml(over / path, "literature/v1"))


def verifies(doc: dict[str, Any], public: str) -> None:
    assert doc["key"].split()[:2] == public.split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # ssh-keygen -Y verify, the gate's verifier
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)


# --- confirmations -------------------------------------------------------------------------------


def test_a_steward_session_confirms_a_proposal(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """The signed record names the proposal, is the steward's login, and verifies under the
    approval key; it sits at literature/<ts>-<login>.yaml on an append/ branch."""
    r = post(h, sign_in(h, "code_alice"), body())
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("append/")
    assert out["path"] == f"{NODE_DIR}/literature/20260909T120000Z-{STEWARD}.yaml"
    doc = landed(h, tree, r)
    assert (doc["contributor"], doc["date"]) == (STEWARD, "2026-09-09T12:00:00Z")
    assert (doc["node"], doc["status"], doc["confirms"]) == (NODE, "known", PROPOSAL)
    assert doc["via"] == "approval-key" and doc["model_and_tooling"] is None
    assert doc["references"] == body()["references"] and doc["summary"] == body()["summary"]
    verifies(doc, approval[1])
    assert h.githost.pushes[-1].author is not None
    assert h.githost.pushes[-1].author.name == STEWARD
    (pr,) = h.githost.pulls
    assert pr.title == f"literature: {NODE} confirmed by {STEWARD}"
    assert "literature confirmation" in pr.body and "approval key" in pr.body


def test_a_curator_states_the_status_without_a_proposal(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """``record: null``: the signer's own reading, confirming nothing; the products take it as
    the confirmed status directly."""
    r = post(h, sign_in(h, "code_owner"), body(record=None, status="elementary"))
    doc = landed(h, tree, r)
    assert (doc["contributor"], doc["status"], doc["confirms"]) == (CURATOR, "elementary", None)
    verifies(doc, approval[1])


def test_a_bearer_with_a_github_login_confirms_too(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """An agent working for a steward through the MCP: the same route, a bearer instead of the
    cookie, the identity's GitHub login as the signer (as POST /stewards accepts)."""
    token = h.token_for("code_alice", "alice-agent")  # the pseudonym is not the login
    r = h.client.post(ROUTE, json=body(), headers=h.auth(token))
    doc = landed(h, tree, r)
    assert doc["contributor"] == STEWARD
    assert r.json()["path"].endswith(f"-{STEWARD}.yaml")
    verifies(doc, approval[1])


def test_a_confirmation_may_correct_the_proposed_status(h: Harness, tree: Path) -> None:
    """D-32 v3.35: the steward confirms *or corrects*; the record it names stays untouched."""
    r = post(h, sign_in(h, "code_alice"), body(status="open"))
    doc = landed(h, tree, r)
    assert (doc["status"], doc["confirms"]) == ("open", PROPOSAL)
    assert (tree / NODE_DIR / PROPOSAL).read_text() == yaml.safe_dump(
        proposal_doc(), sort_keys=False
    )


def test_the_submission_is_watchable_under_its_own_kind(h: Harness) -> None:
    out = post(h, sign_in(h, "code_alice"), body()).json()
    r = h.client.get(f"/submissions/{out['pr_number']}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["kind"] == "literature-confirmation"


# --- refusals ------------------------------------------------------------------------------------


def test_a_login_that_is_neither_steward_nor_curator_is_403(h: Harness) -> None:
    r = post(h, sign_in(h, "code_carol"), body())
    assert r.status_code == 403 and r.json()["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_a_tutorial_identity_has_no_login_to_confirm_with(h: Harness) -> None:
    held = Identity("01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z")
    h.store.put_identity(held)
    raw, _ = auth.new_session(h.context, held.id)
    r = post(h, raw, body())
    assert r.status_code == 403 and r.json()["error"] == "github-login-required"
    assert h.githost.pushes == []


def test_no_session_and_no_bearer_is_401(h: Harness) -> None:
    assert h.client.post(ROUTE, json=body()).status_code == 401
    assert h.githost.pushes == []


def test_a_proposal_that_is_not_on_the_node_is_404(h: Harness) -> None:
    r = post(h, sign_in(h, "code_alice"), body(record="literature/20261001T090000Z-nobody.yaml"))
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not-found"
    assert r.json()["details"]["path"].endswith("literature/20261001T090000Z-nobody.yaml")
    assert h.githost.pushes == []


def test_an_unknown_node_is_404(h: Harness) -> None:
    r = post(h, sign_in(h, "code_alice"), body(node_id="no-such-node"))
    assert r.status_code == 404 and r.json()["error"] == "node-unknown"


@pytest.mark.parametrize(
    "over",
    [
        {"record": "attempts/x.yaml"},
        {"record": "literature/../x.yaml"},
        {"record": 7},
        {"status": "hard"},
        {"references": []},
        {"references": [{"title": "x", "url": "ftp://x", "note": None}]},
        {"summary": ""},
    ],
)
def test_bad_arguments_are_400_naming_the_field(h: Harness, over: dict[str, Any]) -> None:
    r = post(h, sign_in(h, "code_alice"), body(**over))
    assert r.status_code == 400, (over, r.text)
    assert r.json()["error"] == "arguments-invalid"
    (field,) = over
    assert r.json()["details"]["field"].startswith(field), (over, r.json())
    assert h.githost.pushes == []


def test_a_record_that_is_not_a_literature_record_is_400(h: Harness, tree: Path) -> None:
    """The named file exists but is something else: refused, since a confirmation names a
    proposal and nothing else (D-25 v3.35)."""
    stray = tree / NODE_DIR / "literature/20261001T090000Z-stray.yaml"
    stray.write_text("schema: postmortem/v1\n", encoding="utf-8")
    serve_tree(h, tree)
    r = post(h, sign_in(h, "code_alice"), body(record="literature/20261001T090000Z-stray.yaml"))
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == "record"


def test_without_the_approval_key_the_route_is_503(tree: Path) -> None:
    """C7: never signed with anything else; the route says what is missing."""
    for h in harness_over(tree, {}):
        r = post(h, sign_in(h, "code_alice"), body())
        assert r.status_code == 503 and r.json()["error"] == "approval-key-missing"
        assert h.githost.pushes == []


def test_the_hourly_limit_is_the_approvals_limit(tree: Path, approval: tuple[str, str]) -> None:
    for h in harness_over(
        tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0], "OPN_API_APPROVALS_PER_HOUR": "1"}
    ):
        alice = sign_in(h, "code_alice")
        assert post(h, alice, body()).status_code == 201
        h.clock.advance(seconds=1)
        r = post(h, alice, body(status="open"))
        assert r.status_code == 429 and r.json()["error"] == "rate-limited"
        assert r.headers["Retry-After"]
