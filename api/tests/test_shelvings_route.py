"""F31-T7 (R6, AC6): ``POST /shelvings`` (D-14, D-32, D-35 v3.47).

A steward of the node's target, or a listed curator, shelves a statement (or one of its merged
decompositions), or lifts a shelving, from the site (the F23 web session) or with a bearer whose
identity is a GitHub login. The service writes a signed ``shelving/v1`` record as that login,
``via: approval-key``, signed over the canonical body exactly as a literature confirmation is
(``stewards.sign_record``), and opens one pull request on an ``append/`` branch. What lands is
what is tested: the pushed file laid over the graph, validated against its schema, its signature
checked by ``ssh-keygen -Y verify`` and by the service's own reader. Anyone else is 403; the root
and a statement a merged proof uses are 409; a route that is not the node's is 404; an act the
row already says is 409.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_glosses_route import CURATOR, NODE, NODE_DIR, TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import auth, identity, shelvings, sshsig
from opn_api.githost import GitHubUser
from opn_api.store import Identity
from opn_gate import schemas, signed
from opn_gate.signer import NAMESPACE, SshKeygenSigner

ROUTE = "/shelvings"
STEWARD = "alice"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
ROOT = "and-swap-reassoc"  # the fixture graph.json's declared root
PARTIAL = "attempts/20261023T120000Z-t1023-f1.lean"
HOLE = f"{NODE}--h1"
CAUSE = "Route 2 proves fourteen special cases and nothing the root needs."


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
    """The propositional fixture (alice a steward, the owner a curator)."""
    return make_tree(tmp_path, keys)


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


def set_row(h: Harness, node_id: str, **fields: Any) -> None:
    """One ``graph.json`` row written or rewritten in the committed product (graph/v15's
    fields default to their empty values, so a test names only what it is about)."""
    doc = json.loads(h.githost.files[GRAPH_PATH])
    old = next((n for n in doc["nodes"] if n["node_id"] == node_id), None)
    row = {
        "node_id": node_id,
        "status": "ready",
        "cause": None,
        "deps": [],
        "origin": "authored",
        "statement_hash": "3" * 64,
        "relation": None,
        "tutorial": False,
        "trust_base": None,
        "proof_commit": None,
        "proofs": [],
        "decompositions": [],
        "closure": None,
        "shelved": None,
        **(old or {}),
        **fields,
    }
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != node_id] + [row]
    h.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    h.context.files.clear()


def decomposition(partial: str = PARTIAL, *holes: str) -> dict[str, Any]:
    return {
        "partial": partial,
        "annex": None,
        "approach": None,
        "holes": [{"name": f"h{i + 1}", "node": node} for i, node in enumerate(holes)],
    }


def body(**over: Any) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "action": "shelved",
        "scope": "node",
        "route": None,
        "cause": CAUSE,
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
    return dict(schemas.load_yaml(over / path, shelvings.SCHEMA))


def verifies(doc: dict[str, Any], public: str) -> None:
    assert doc["key"].split()[:2] == public.split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # ssh-keygen -Y verify, the gate's verifier
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)


def shelved_object(**over: Any) -> dict[str, Any]:
    return {
        "cause": CAUSE,
        "by": STEWARD,
        "date": "2026-09-09",
        "record": f"shelving/20260909T120000Z-{STEWARD}.yaml",
        "scope": "node",
        "via": NODE,
    } | over


# --- the act -------------------------------------------------------------------------------------


def test_a_steward_session_shelves_a_statement(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """The signed record is the steward's login, verifies under the approval key, and sits at
    shelving/<ts>-<login>.yaml on an append/ branch, in the schema's field order."""
    r = post(h, sign_in(h, "code_alice"), body())
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("append/")
    assert out["path"] == f"{NODE_DIR}/shelving/20260909T120000Z-{STEWARD}.yaml"
    doc = landed(h, tree, r)
    assert (doc["contributor"], doc["date"]) == (STEWARD, "2026-09-09T12:00:00Z")
    assert (doc["node"], doc["action"], doc["scope"], doc["route"]) == (
        NODE,
        "shelved",
        "node",
        None,
    )
    assert doc["cause"] == CAUSE and doc["via"] == "approval-key"
    assert list(doc) == [
        "schema",
        "node",
        "action",
        "scope",
        "route",
        "cause",
        "contributor",
        "date",
        "via",
        "key",
        "signature",
    ]
    verifies(doc, approval[1])
    assert h.githost.pushes[-1].author is not None
    assert h.githost.pushes[-1].author.name == STEWARD
    (pr,) = h.githost.pulls
    assert pr.title == f"shelving: {NODE} shelved by {STEWARD}"
    assert "shelving" in pr.body and "approval key" in pr.body


def test_a_curator_retires_a_route(h: Harness, tree: Path, approval: tuple[str, str]) -> None:
    """``scope: route`` names one of the node's merged decompositions by its file."""
    set_row(h, NODE, decompositions=[decomposition(PARTIAL, HOLE)])
    r = post(h, sign_in(h, "code_owner"), body(scope="route", route=PARTIAL))
    doc = landed(h, tree, r)
    assert (doc["contributor"], doc["scope"], doc["route"]) == (CURATOR, "route", PARTIAL)
    verifies(doc, approval[1])
    (pr,) = h.githost.pulls
    assert pr.title == f"shelving: {NODE} route retired by {CURATOR}"


def test_a_bearer_with_a_github_login_shelves_too(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """An agent working for a steward: the same route, a bearer instead of the cookie, the
    identity's GitHub login as the signer."""
    token = h.token_for("code_alice", "alice-agent")  # the pseudonym is not the login
    r = h.client.post(ROUTE, json=body(), headers=h.auth(token))
    doc = landed(h, tree, r)
    assert doc["contributor"] == STEWARD
    assert r.json()["path"].endswith(f"-{STEWARD}.yaml")
    verifies(doc, approval[1])


def test_an_unshelve_lifts_a_shelved_node(h: Harness, tree: Path) -> None:
    set_row(h, NODE, shelved=shelved_object())
    r = post(h, sign_in(h, "code_alice"), body(action="unshelved", cause="Needed after all."))
    doc = landed(h, tree, r)
    assert (doc["action"], doc["cause"]) == ("unshelved", "Needed after all.")
    (pr,) = h.githost.pulls
    assert pr.title == f"shelving: {NODE} unshelved by {STEWARD}"


def test_an_unshelve_on_an_inherited_shelving_is_how_a_child_is_exempted(
    h: Harness, tree: Path
) -> None:
    """Q3: a hole child under a shelved parent may be lifted by its own record; the row says
    shelved via the parent, and the act still changes something."""
    set_row(h, NODE, shelved=shelved_object(via=ROOT, record="shelving/x.yaml"))
    r = post(h, sign_in(h, "code_alice"), body(action="unshelved", cause="Keep this one."))
    assert r.status_code == 201, r.text


def test_a_node_shelved_by_inheritance_may_still_carry_its_own_record(
    h: Harness, tree: Path
) -> None:
    """Its own record decides for it before any inherited shelving (rule 4), so the act changes
    what an unshelving of the ancestor does; only a node whose own record says so is refused."""
    set_row(h, NODE, shelved=shelved_object(via=ROOT, record="shelving/x.yaml"))
    r = post(h, sign_in(h, "code_alice"), body())
    assert r.status_code == 201, r.text


def test_the_submission_is_watchable_under_its_own_kind(h: Harness) -> None:
    out = post(h, sign_in(h, "code_alice"), body()).json()
    r = h.client.get(f"/submissions/{out['pr_number']}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["kind"] == shelvings.KIND


# --- refusals ------------------------------------------------------------------------------------


def test_a_login_that_is_neither_steward_nor_curator_is_403(h: Harness) -> None:
    r = post(h, sign_in(h, "code_carol"), body())
    assert r.status_code == 403 and r.json()["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_a_tutorial_identity_has_no_login_to_shelve_with(h: Harness) -> None:
    held = Identity(
        "01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z", identity.DCO_VERSION
    )
    h.store.put_identity(held)
    raw, _ = auth.new_session(h.context, held.id)
    r = post(h, raw, body())
    assert r.status_code == 403 and r.json()["error"] == "github-login-required"
    assert h.githost.pushes == []


def test_no_session_and_no_bearer_is_401(h: Harness) -> None:
    assert h.client.post(ROUTE, json=body()).status_code == 401
    assert h.githost.pushes == []


def test_the_root_is_409_node_root(h: Harness) -> None:
    set_row(h, ROOT)
    r = post(h, sign_in(h, "code_alice"), body(node_id=ROOT))
    assert r.status_code == 409 and r.json()["error"] == "node-root", r.text
    assert h.githost.pushes == []


def test_a_statement_a_merged_proof_uses_is_409_node_used(h: Harness) -> None:
    """``proofs[].used`` on any row of the target names it (F18): it may not be shelved."""
    set_row(
        h,
        "already-proved",
        proofs=[
            {
                "kind": "proof",
                "path": "Proof.lean",
                "artifact_hash": "4" * 64,
                "attestation": "000001.json",
                "merge_commit": "5" * 40,
                "submitter": None,
                "used": [NODE],
            }
        ],
    )
    r = post(h, sign_in(h, "code_alice"), body())
    assert r.status_code == 409 and r.json()["error"] == "node-used", r.text
    assert r.json()["details"]["used_by"] == ["already-proved"]
    assert h.githost.pushes == []


def test_an_input_of_a_closure_link_is_409_node_used(h: Harness) -> None:
    set_row(
        h,
        "already-proved",
        closure={"kind": "route", "id": "r1", "inputs": [NODE], "record": "closing/x.yaml"},
    )
    r = post(h, sign_in(h, "code_alice"), body())
    assert r.status_code == 409 and r.json()["error"] == "node-used", r.text
    assert r.json()["details"]["used_by"] == ["already-proved"]


def test_a_route_that_is_not_the_nodes_is_404(h: Harness) -> None:
    set_row(h, NODE, decompositions=[decomposition("attempts/other.lean", HOLE)])
    r = post(h, sign_in(h, "code_alice"), body(scope="route", route=PARTIAL))
    assert r.status_code == 404 and r.json()["error"] == "shelving-route-unknown", r.text
    assert r.json()["details"]["routes"] == ["attempts/other.lean"]
    assert h.githost.pushes == []


def test_an_already_shelved_node_is_409(h: Harness) -> None:
    set_row(h, NODE, shelved=shelved_object())
    r = post(h, sign_in(h, "code_alice"), body())
    assert r.status_code == 409 and r.json()["error"] == "already-shelved", r.text
    assert r.json()["details"]["shelved"] == shelved_object()
    assert h.githost.pushes == []


def test_a_route_whose_holes_are_all_retired_is_409(h: Harness) -> None:
    set_row(h, NODE, decompositions=[decomposition(PARTIAL, HOLE)])
    set_row(h, HOLE, origin="skeleton-hole", shelved=shelved_object(scope="route", via=NODE))
    r = post(h, sign_in(h, "code_alice"), body(scope="route", route=PARTIAL))
    assert r.status_code == 409 and r.json()["error"] == "already-shelved", r.text


def test_an_unshelve_on_a_node_that_is_not_shelved_is_409(h: Harness) -> None:
    r = post(h, sign_in(h, "code_alice"), body(action="unshelved"))
    assert r.status_code == 409 and r.json()["error"] == "not-shelved", r.text
    assert h.githost.pushes == []


def test_an_unknown_node_is_404(h: Harness) -> None:
    r = post(h, sign_in(h, "code_alice"), body(node_id="no-such-node"))
    assert r.status_code == 404 and r.json()["error"] == "node-unknown"


@pytest.mark.parametrize(
    "over",
    [
        {"action": "retired"},
        {"action": None},
        {"scope": "target"},
        {"route": PARTIAL},  # scope node with a route
        {"scope": "route", "route": None},
        {"scope": "route", "route": "attempts/../x.lean"},
        {"scope": "route", "route": "annex/x.md"},
        {"cause": ""},
        {"cause": "x" * 1001},
        {"cause": 7},
    ],
)
def test_bad_arguments_are_400_naming_the_field(h: Harness, over: dict[str, Any]) -> None:
    r = post(h, sign_in(h, "code_alice"), body(**over))
    assert r.status_code == 400, (over, r.text)
    assert r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] in over, (over, r.json())
    assert h.githost.pushes == []


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
        r = post(h, alice, body(node_id="tutorial-and-swap"))
        assert r.status_code == 429 and r.json()["error"] == "rate-limited"
        assert r.headers["Retry-After"]
