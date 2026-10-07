"""F23-T6 / AC7 (service half): ``POST /approvals`` (R10; D-3 v3.33, D-32 v3.33).

A signed-in steward of the target, or a curator, approves sections of one gloss or explainer
version, and the service writes ``gloss-signature/v3`` or ``explainer-signature/v3`` as that
login, signs it with the network's approval key and opens it on an ``append/`` branch. Any other
login is 403. What lands is what is tested: the pushed file laid over the graph, validated
against its schema, and its signature checked by ``ssh-keygen -Y verify`` and by the service's
own reader. (The products' half of AC7 — sections verified, the author credited — is the gate's,
``gate/tests/test_signature_v3.py``.)
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, NODE, NODE_DIR, TARGET, make_keys, make_tree, put_version
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import sshsig
from opn_api.githost import GitHubUser
from opn_gate import explainers, glosses, schemas, signed
from opn_gate.signer import NAMESPACE, SshKeygenSigner


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


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def versions(tree: Path) -> dict[str, str]:
    """One gloss of the node's statement and one explainer of its proof, both merged."""
    return {
        "gloss": put_version(tree, "gloss", "Associativity of conjunction.\n"),
        "explainer": put_version(tree, "explainer", "Regroup the conjuncts."),
    }


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    serve_tree(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, versions: dict[str, str], approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


def body(kind: str, version: str, **over: Any) -> dict[str, Any]:
    return {
        "target": TARGET,
        "node": NODE,
        "kind": kind,
        "version": version,
        "sections": None,
    } | over


def post(h: Harness, cookie: str, doc: dict[str, Any]) -> Any:
    return h.client.post("/approvals", json=doc, headers=web_headers(cookie))


def landed(h: Harness, tree: Path, response: Any, schema_id: str) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    assert list(push.files) == [path]
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    (over / path).parent.mkdir(parents=True, exist_ok=True)
    (over / path).write_text(push.files[path], encoding="utf-8")
    return dict(schemas.load_yaml(over / path, schema_id))


def verifies(doc: dict[str, Any], public: str) -> None:
    assert doc["key"].split()[:2] == public.split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # ssh-keygen -Y verify, the gate's verifier
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)


def test_a_steward_approves_a_gloss(
    h: Harness, tree: Path, versions: dict[str, str], approval: tuple[str, str]
) -> None:
    """AC7: a steward session gets a v3 signature pull request on an append/ branch."""
    r = post(h, sign_in(h, "code_alice"), body("gloss", versions["gloss"], sections=["whole"]))
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("append/")
    assert out["path"] == f"{NODE_DIR}/gloss/signed/{versions['gloss']}-1.yaml"
    doc = landed(h, tree, r, "gloss-signature/v3")
    assert (doc["signer"], doc["via"], doc["date"]) == ("alice", "approval-key", "2026-09-09")
    assert doc["affirmation"] == glosses.AFFIRMATION
    assert (doc["target"], doc["node"], doc["gloss"]) == (TARGET, NODE, versions["gloss"])
    assert doc["sections"] == ["whole"]
    verifies(doc, approval[1])
    assert h.githost.pushes[-1].author is not None
    assert h.githost.pushes[-1].author.name == "alice"


def test_a_curator_approves_an_explainers_sections(
    h: Harness, tree: Path, versions: dict[str, str], approval: tuple[str, str]
) -> None:
    keys = explainers.section_keys(tree / NODE_DIR / "explainer" / f"{versions['explainer']}.md")
    assert keys
    r = post(h, sign_in(h, "code_owner"), body("explainer", versions["explainer"], sections=keys))
    assert r.json()["path"] == f"{NODE_DIR}/explainer/signed/{versions['explainer']}-1.yaml"
    doc = landed(h, tree, r, "explainer-signature/v3")
    assert doc["signer"] == CURATOR and doc["affirmation"] == explainers.AFFIRMATION
    assert doc["explainer"] == versions["explainer"] and doc["sections"] == keys
    verifies(doc, approval[1])


def test_no_sections_approves_the_whole_version(
    h: Harness, tree: Path, versions: dict[str, str]
) -> None:
    """The schema: an absent ``sections`` approves every section of the version."""
    doc = landed(
        h,
        tree,
        post(h, sign_in(h, "code_alice"), body("gloss", versions["gloss"])),
        "gloss-signature/v3",
    )
    assert "sections" not in doc


def test_the_next_signature_of_a_version_is_numbered_after_the_last(
    h: Harness, tree: Path, versions: dict[str, str]
) -> None:
    alice = sign_in(h, "code_alice")
    first = post(h, alice, body("gloss", versions["gloss"]))
    path = first.json()["path"]
    (tree / path).parent.mkdir(parents=True, exist_ok=True)
    (tree / path).write_text(h.githost.pushes[-1].files[path], encoding="utf-8")
    serve_tree(h, tree)
    owner = post(h, sign_in(h, "code_owner"), body("gloss", versions["gloss"]))
    assert owner.json()["path"].endswith(f"{versions['gloss']}-2.yaml")


# --- refusals ------------------------------------------------------------------------------------


def test_a_login_that_is_neither_steward_nor_curator_is_403(
    h: Harness, versions: dict[str, str]
) -> None:
    """AC7: a non-steward session is refused, and nothing is pushed."""
    r = post(h, sign_in(h, "code_carol"), body("gloss", versions["gloss"]))
    assert r.status_code == 403 and r.json()["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_no_session_is_401(h: Harness, versions: dict[str, str]) -> None:
    assert h.client.post("/approvals", json=body("gloss", versions["gloss"])).status_code == 401


def test_an_unknown_version_is_404(h: Harness, versions: dict[str, str]) -> None:
    alice = sign_in(h, "code_alice")
    r = post(h, alice, body("gloss", "0" * 64))
    assert r.status_code == 404 and r.json()["error"] == "version-unknown"
    wrong_kind = post(h, alice, body("explainer", versions["gloss"]))
    assert wrong_kind.status_code == 404


@pytest.mark.parametrize(
    "over",
    [
        {"kind": "annex"},
        {"version": "abc"},
        {"sections": []},
        {"sections": ["overview"]},  # a gloss has one section, whole
        {"sections": ["whole", "whole"]},
        {"sections": "whole"},
        {"node": 3},
        {"target": ""},
    ],
)
def test_bad_arguments_are_400(h: Harness, versions: dict[str, str], over: dict[str, Any]) -> None:
    r = post(h, sign_in(h, "code_alice"), body("gloss", versions["gloss"]) | over)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert h.githost.pushes == []


def test_an_explainer_section_it_does_not_have_is_400(h: Harness, versions: dict[str, str]) -> None:
    r = post(
        h,
        sign_in(h, "code_alice"),
        body("explainer", versions["explainer"], sections=["steps:nope"]),
    )
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid"


def test_an_explainer_needs_its_node(h: Harness, versions: dict[str, str]) -> None:
    r = post(h, sign_in(h, "code_alice"), body("explainer", versions["explainer"], node=None))
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid"


def test_an_unknown_target_is_404(h: Harness, versions: dict[str, str]) -> None:
    r = post(h, sign_in(h, "code_alice"), body("gloss", versions["gloss"], target="nope"))
    assert r.status_code == 404


def test_without_the_approval_key_the_route_is_503(tree: Path, versions: dict[str, str]) -> None:
    for h in harness_over(tree, {}):
        r = post(h, sign_in(h, "code_alice"), body("gloss", versions["gloss"]))
        assert r.status_code == 503 and r.json()["error"] == "approval-key-missing"


def test_sixty_an_hour_per_login(h: Harness, versions: dict[str, str]) -> None:
    carol = sign_in(h, "code_carol")
    for _ in range(60):
        assert post(h, carol, body("gloss", versions["gloss"])).status_code == 403
    r = post(h, carol, body("gloss", versions["gloss"]))
    assert r.status_code == 429 and "retry-after" in r.headers
