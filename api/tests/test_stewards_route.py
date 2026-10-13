"""F23-T5 / AC5: ``POST /stewards`` (R8; D-32 v3.33, D-23).

A signed-in login asks for the steward role (or steps down) and the service writes the
``steward/v2`` record as that login, signs it with the network's approval key and opens its pull
request with the identity as author. The shape that lands is what is tested: the pushed file is
laid over the graph tree, validated against the published schema, and its signature checked by
the gate's verifier (``ssh-keygen -Y verify``) and by the service's own reader.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, TARGET, make_keys, make_tree, serve
from test_web_session import ENV, sign_in, web_headers

from opn_api import auth, identity, sshsig
from opn_api.githost import GitHubUser
from opn_api.store import Identity
from opn_gate import schemas, signed, steward
from opn_gate.signer import NAMESPACE, SshKeygenSigner

STEWARDS = f"targets/{TARGET}/stewards"
#: A defect in T1's published schema, held strict so the fix flips these red until the mark comes
#: off: steward/v2's ``admitted_by`` is a ``oneOf`` of ``const: self`` and the login pattern, and
#: ``self`` matches both, so every self-admitted record (all of them under ``open``) fails
#: validation and the route refuses it 400 ``record-invalid``. With ``anyOf`` there every test
#: here passes (engineering/evidence/F23/task-5.txt).
FORM = {"target": TARGET, "action": "commit", "name": "Carol C.", "link": None, "accept": True}


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture(scope="module")
def approval(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    """The network's approval key pair (C8): private text for the service, public for the graph."""
    key = tmp_path_factory.mktemp("approval") / "approval"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "approval"],
        check=True,
    )
    return key.read_text(), key.with_suffix(".pub").read_text().strip()


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    serve(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


def post(h: Harness, cookie: str, **over: Any) -> Any:
    return h.client.post("/stewards", json={**FORM, **over}, headers=web_headers(cookie))


def landed(h: Harness, tree: Path, response: Any) -> dict[str, Any]:
    """The one pushed file, laid over a copy of the graph and read back through the schema."""
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    assert list(push.files) == [response.json()["path"]]
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    path = over / response.json()["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(push.files[response.json()["path"]], encoding="utf-8")
    return dict(schemas.load_yaml(path, "steward/v2"))


def merge(h: Harness, tree: Path, response: Any) -> None:
    """The pull request merged: its file is on ``main``."""
    path = response.json()["path"]
    (tree / path).write_text(h.githost.pushes[-1].files[path], encoding="utf-8")
    serve(h, tree)


def test_commit_under_open_is_a_signed_self_admitted_append(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """AC5: an ``append/`` pull request whose one file is a ``steward/v2`` record that verifies
    under the approval key, with ``admitted_by: self``, authored by the identity (D-23)."""
    r = post(h, sign_in(h, "code_carol"))
    body = r.json()
    assert set(body) == {"pr_number", "pr_url", "branch", "path"}
    assert body["branch"].startswith("append/")
    assert body["path"] == f"{STEWARDS}/2.yaml"  # alice's SSH commit is 1.yaml
    doc = landed(h, tree, r)
    assert doc["login"] == "carol" and doc["name"] == "Carol C." and doc["link"] is None
    assert doc["action"] == "commit" and doc["commitment"] == steward.COMMITMENT
    assert (doc["via"], doc["admitted_by"], doc["date"]) == ("approval-key", "self", "2026-09-09")
    assert doc["key"].split()[:2] == approval[1].split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # ssh-keygen -Y verify, the gate's verifier
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)
    push = h.githost.pushes[-1]
    assert push.author is not None and push.author.name == "carol"
    assert h.githost.pulls[-1].head == body["branch"]


def test_a_second_commit_restates_the_name(h: Harness, tree: Path) -> None:
    """F24-T7 (F24-Q15): a commitment from an active steward is a restatement, not a 409: it
    carries the new name and link and the admission of the commitment it restates, on an
    ``append/`` branch, since it admits nobody. (Until F24-T7 this was ``steward-already-active``,
    and a steward could never change the name the page shows.)"""
    carol = sign_in(h, "code_carol")
    merge(h, tree, post(h, carol))
    again = post(h, carol, name="Carol Cole", link="https://example.org/carol")
    assert again.status_code == 201, again.text
    assert again.json()["branch"].startswith("append/")
    doc = landed(h, tree, again)
    assert (doc["name"], doc["link"]) == ("Carol Cole", "https://example.org/carol")
    assert (doc["action"], doc["admitted_by"]) == ("commit", "self")


def test_the_same_form_sent_twice_is_one_submission(h: Harness) -> None:
    """The duplicate guard still holds a double click to one pull request, now that a
    restatement with a new name is a submission of its own (F24-T7)."""
    carol = sign_in(h, "code_carol")
    assert post(h, carol).status_code == 201
    again = post(h, carol)
    assert again.status_code == 409 and again.json()["error"] == "duplicate-submission"


def test_an_active_v1_steward_restates_as_self(h: Harness, tree: Path) -> None:
    """alice's ``steward/v1`` commitment names no admission; her restatement says ``self``,
    which the gate accepts of a v1 one (F24-T7)."""
    r = post(h, sign_in(h, "code_alice"), name="Alice A.")
    doc = landed(h, tree, r)
    assert (doc["login"], doc["name"], doc["admitted_by"]) == ("alice", "Alice A.", "self")


def stand(tree: Path, n: int, login: str, admitted_by: str) -> None:
    """A commitment already on ``main``: the service does not verify signatures (R9 is the
    gate's), so the record's facts are enough."""
    doc = {
        "schema": "steward/v3",
        "target": TARGET,
        "action": "commit",
        "login": login,
        "name": login.title(),
        "link": None,
        "commitment": steward.COMMITMENT,
        "date": "2026-09-01",
        "via": "approval-key",
        "admitted_by": admitted_by,
    }
    (tree / STEWARDS / f"{n}.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_an_invited_stewards_restatement_names_the_invitation(h: Harness, tree: Path) -> None:
    """The panel keeps an invited steward off motions put before the invitation by reading
    ``motion:<n>`` (F24-T5 Q-a), so a restatement saying ``self`` would seat them there; it
    carries the motion, which only ``steward/v3`` can say."""
    stand(tree, 2, "carol", "motion:1")
    serve(h, tree)
    r = post(h, sign_in(h, "code_carol"), name="Carol Cole")
    assert r.status_code == 201, r.text
    path = tree / r.json()["path"]
    path.write_text(h.githost.pushes[-1].files[r.json()["path"]], encoding="utf-8")
    doc = schemas.load_yaml(path, "steward/v3")
    assert (doc["admitted_by"], doc["name"]) == ("motion:1", "Carol Cole")


def test_under_reviewed_a_restatement_needs_no_curator(
    tree: Path, approval: tuple[str, str]
) -> None:
    """A restatement admits nobody, so it goes to ``append/`` for the merge actor, carrying the
    curator who admitted the steward (F24-T7)."""
    policy = {
        "schema": "policy/v2",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "reviewed",
    }
    (tree / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    stand(tree, 2, "carol", CURATOR)
    for h in harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]}):
        r = post(h, sign_in(h, "code_carol"), name="Carol Cole")
        assert r.json()["branch"].startswith("append/")
        assert landed(h, tree, r)["admitted_by"] == CURATOR


def test_step_down_needs_an_active_commitment(h: Harness, tree: Path) -> None:
    """R8: a step-down from a login that is not active is 409; alice's v1 commit can be ended
    by a v2 step-down (R9)."""
    r = post(h, sign_in(h, "code_carol"), action="step-down")
    assert r.status_code == 409 and r.json()["error"] == "steward-not-active"
    down = post(h, sign_in(h, "code_alice"), action="step-down", name="Alice")
    doc = landed(h, tree, down)
    assert doc["action"] == "step-down" and doc["commitment"] == steward.STEP_DOWN_SENTENCE
    assert doc["login"] == "alice"


def test_reviewed_admission_opens_a_curate_branch_naming_the_curator(
    tree: Path, approval: tuple[str, str]
) -> None:
    """AC5: under ``reviewed`` the branch is ``curate/``, which the merge actor leaves alone."""
    policy = {
        "schema": "policy/v2",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
        "steward_admission": "reviewed",
    }
    (tree / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    for h in harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]}):
        r = post(h, sign_in(h, "code_carol"))
        assert r.json()["branch"].startswith("curate/")
        assert landed(h, tree, r)["admitted_by"] == CURATOR


def test_a_policy_v1_file_means_open(tree: Path, approval: tuple[str, str]) -> None:
    policy = {
        "schema": "policy/v1",
        "steward_rule": {"enforced": False, "since": None, "evidence": None},
    }
    (tree / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    for h in harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]}):
        r = post(h, sign_in(h, "code_carol"))
        assert r.json()["branch"].startswith("append/")
        assert landed(h, tree, r)["admitted_by"] == "self"


def test_a_bearer_token_works_too(h: Harness, tree: Path) -> None:
    token = h.token_for("code_carol", "carol")
    r = h.client.post("/stewards", json=FORM, headers=h.auth(token))
    assert landed(h, tree, r)["login"] == "carol"


# --- refusals ------------------------------------------------------------------------------------


def test_no_session_is_401(h: Harness) -> None:
    r = h.client.post("/stewards", json=FORM)
    assert r.status_code == 401
    assert h.githost.pushes == []


def test_a_tutorial_identity_has_no_login_to_steward_with(h: Harness) -> None:
    held = Identity(
        "01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z", identity.DCO_VERSION
    )
    h.store.put_identity(held)
    raw, _ = auth.new_session(h.context, held.id)
    r = post(h, raw)
    assert r.status_code == 403 and r.json()["error"] == "github-login-required"


@pytest.mark.parametrize(
    "over",
    [
        {"action": "promote"},
        {"accept": False},
        {"accept": None},
        {"name": ""},
        {"name": "x" * 201},
        {"link": "http://example.org/me"},
        {"link": 7},
        {"target": ""},
    ],
)
def test_bad_arguments_are_400(h: Harness, over: dict[str, Any]) -> None:
    r = post(h, sign_in(h, "code_carol"), **over)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert h.githost.pushes == []


def test_an_unknown_target_is_404(h: Harness) -> None:
    r = post(h, sign_in(h, "code_carol"), target="no-such-target")
    assert r.status_code == 404 and r.json()["error"] == "target-unknown"


def test_without_the_approval_key_the_route_is_503(tree: Path) -> None:
    """C7: never signed with anything else; the route says what is missing."""
    for h in harness_over(tree, {}):
        r = post(h, sign_in(h, "code_carol"))
        assert r.status_code == 503 and r.json()["error"] == "approval-key-missing"
        assert h.githost.pushes == []


def test_five_a_day_per_login(h: Harness) -> None:
    """F23 §6: the sixth request of a day is 429, whatever became of the first five."""
    alice = sign_in(h, "code_alice")
    for i in range(5):  # restatements (F24-T7); refused or not, each is a request of the day
        assert post(h, alice, name=f"Alice {i}").status_code != 429
    r = post(h, alice, name="Alice")
    assert r.status_code == 429 and "retry-after" in r.headers


def test_the_record_number_follows_the_highest(h: Harness, tree: Path) -> None:
    (tree / STEWARDS / "7.yaml").write_text(
        (tree / STEWARDS / "1.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    serve(h, tree)
    r = post(h, sign_in(h, "code_carol"))
    assert r.json()["path"] == f"{STEWARDS}/8.yaml"
    assert yaml.safe_load(h.githost.pushes[-1].files[r.json()["path"]])["login"] == "carol"
