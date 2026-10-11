"""F25-T4 / AC15: ``POST /registrations`` and the ``register_target`` and ``list_registrations``
tools (F25-R5, R7, R15; D-10, D-28, D-35 v3.37).

A signed-in curator or an active steward of the target — a web session, or a bearer whose
identity is a GitHub login — records a submission to, or a registration in, Palomar. The service
writes the ``registration/v1`` record as that login (``submitted_by`` is the sign-in, never a
field), names the file ``registrations/<date>-<n>.yaml`` and opens it on an ``append/`` branch,
which the graph's merge actor takes without any change (its ``SERVICE_PREFIXES`` are ``propose/``,
``append/``, ``submit/``). It refuses by name what the gate would refuse — the submitter's role,
the proof's node, the attestation — with nothing opened, and what lands is checked by the gate's
own ``modes.check_as_service`` over the tree it will merge into. Nothing here talks to the
registry: the submission is the curator's act outside the network.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import CURATOR, TARGET, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import auth, identity
from opn_api.githost import GitHubUser
from opn_api.store import Identity
from opn_gate import modes, schemas
from opn_gate.signer import SshKeygenSigner

ROUTE = "/registrations"
NODE = "and-reassoc"
STEWARD = "alice"
ATTESTATION = "000038"
SHA = "a" * 40


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


def attest(tree: Path, number: str, **overrides: Any) -> None:
    where = tree / "attestations"
    where.mkdir(exist_ok=True)
    doc = samples.attestation(graph_id=TARGET, **({"node_id": NODE} | overrides))
    (where / f"{number}.json").write_bytes(schemas.canonical_json(doc))


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    """The propositional fixture (alice a steward, the owner a curator) with a passing attestation
    of the node's merge on the graph."""
    root = make_tree(tmp_path, keys)
    attest(root, ATTESTATION)
    return root


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    h.githost.users["code_owner"] = GitHubUser(CURATOR, 7, "2015-01-01T00:00:00Z")
    h.githost.users["code_carol"] = GitHubUser("carol", 1003, "2019-01-01T00:00:00Z")
    serve_tree(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from harness_over(tree, {})


def body(**over: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "target_id": TARGET,
        "registry": "palomar",
        "registry_id": "PALOMAR-2026-10-12-000003",
        "version": 1,
        "wrapper": {"repository": "open-proof-network/palomar-propositional", "commit": SHA},
        "graph_commit": "b" * 40,
        "proof": {"node": NODE, "attestation": ATTESTATION},
        "status": "registered",
        "url": "https://palomar-registry.org/entries/PALOMAR-2026-10-12-000003",
        "challenge_sha256": "c" * 64,
        "solution_sha256": "d" * 64,
        "note": "Registered after the review.",
    }
    return doc | over


def post(h: Harness, cookie: str, doc: dict[str, Any]) -> Any:
    return h.client.post(ROUTE, json=doc, headers=web_headers(cookie))


def landed(h: Harness, tree: Path, response: Any) -> tuple[dict[str, Any], str]:
    """The pushed file laid over the tree, validated, and the gate's own verdict on it."""
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    assert list(push.files) == [path]
    over = tree.parent / "landed"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    problems = modes.check_as_service(
        over, path, push.files[path].encode(), signer=SshKeygenSigner()
    )
    (over / path).write_text(push.files[path], encoding="utf-8")
    doc = dict(schemas.load_yaml(over / path, "registration/v1"))
    return doc, "; ".join(d.code for d in problems)


# --- the record ----------------------------------------------------------------------------------


def test_a_curator_session_records_a_registration(h: Harness, tree: Path) -> None:
    r = post(h, sign_in(h, "code_owner"), body())
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("append/"), "the merge actor takes append/ as it is"
    assert out["path"] == f"targets/{TARGET}/registrations/2026-09-09-1.yaml"
    doc, verdict = landed(h, tree, r)
    assert verdict == "", "the gate admits what the service wrote"
    assert (doc["target"], doc["submitted_by"], doc["date"]) == (TARGET, CURATOR, "2026-09-09")
    assert doc["proof"] == {"node": NODE, "attestation": ATTESTATION}
    assert (doc["registry"], doc["registry_id"], doc["version"]) == (
        "palomar",
        body()["registry_id"],
        1,
    )
    assert (doc["status"], doc["url"], doc["note"]) == ("registered", body()["url"], body()["note"])
    assert doc["wrapper"] == body()["wrapper"] and doc["graph_commit"] == "b" * 40
    # The commit's author is the identity (its pseudonym, D-23); submitted_by is the login.
    assert h.githost.pushes[-1].author is not None
    (pr,) = h.githost.pulls
    assert pr.title == f"registration: {TARGET} registered by {CURATOR}"
    assert "registration record" in pr.body


def test_a_steward_bearer_records_one_too(h: Harness, tree: Path) -> None:
    token = h.token_for("code_alice", "alice-agent")  # the pseudonym is not the login
    r = h.client.post(ROUTE, json=body(), headers=h.auth(token))
    doc, verdict = landed(h, tree, r)
    assert verdict == ""
    assert doc["submitted_by"] == STEWARD


def test_a_submission_without_an_id_yet(h: Harness, tree: Path) -> None:
    sent = body(
        registry_id=None, version=None, status="submitted", url=None,
        challenge_sha256=None, solution_sha256=None, note=None,
    )  # fmt: skip
    doc, verdict = landed(h, tree, post(h, sign_in(h, "code_owner"), sent))
    assert verdict == ""
    assert (doc["registry_id"], doc["version"], doc["status"], doc["url"]) == (
        None,
        None,
        "submitted",
        None,
    )


def test_optional_fields_may_be_left_out(h: Harness, tree: Path) -> None:
    sent = {
        "target_id": TARGET,
        "registry": "palomar",
        "wrapper": body()["wrapper"],
        "graph_commit": "b" * 40,
        "proof": body()["proof"],
        "status": "withdrawn",
    }
    doc, verdict = landed(h, tree, post(h, sign_in(h, "code_owner"), sent))
    assert verdict == ""
    assert doc["status"] == "withdrawn" and doc["url"] is None and doc["note"] is None


def test_a_second_record_the_same_day_is_numbered_after_the_open_one(
    h: Harness, tree: Path
) -> None:
    """The number is the highest merged under the target that day, plus every record of this
    kind still open for it, plus one: two filed on one day never share a path, and a gap costs
    nothing (the number only tells records apart)."""
    owner = sign_in(h, "code_owner")
    first = post(h, owner, body(status="submitted", registry_id=None, version=None, url=None))
    assert first.json()["path"].endswith("2026-09-09-1.yaml")
    h.clock.advance(
        seconds=90
    )  # past the name hold: the number, not the hold, must tell them apart
    second = post(h, owner, body())
    assert second.status_code == 201, second.text
    assert second.json()["path"].endswith("2026-09-09-2.yaml")
    # And one already merged on the graph counts too: 7 merged, two still open, so 10.
    (tree / "targets" / TARGET / "registrations").mkdir(exist_ok=True)
    (tree / "targets" / TARGET / "registrations" / "2026-09-09-7.yaml").write_text("x: 1\n")
    serve_tree(h, tree)
    h.clock.advance(seconds=90)
    third = post(h, owner, body(version=2))
    assert third.json()["path"].endswith("2026-09-09-10.yaml")


def test_the_submission_is_watchable_under_its_own_kind(h: Harness) -> None:
    out = post(h, sign_in(h, "code_owner"), body()).json()
    r = h.client.get(f"/submissions/{out['pr_number']}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["kind"] == "registration"


# --- refusals, each with nothing opened -----------------------------------------------------------


def test_a_login_that_is_neither_steward_nor_curator_is_403(h: Harness) -> None:
    r = post(h, sign_in(h, "code_carol"), body())
    assert r.status_code == 403 and r.json()["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_a_tutorial_identity_has_no_login_to_register_with(h: Harness) -> None:
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


def test_an_unknown_target_is_404(h: Harness) -> None:
    r = post(h, sign_in(h, "code_owner"), body(target_id="no-such-target"))
    assert r.status_code == 404 and r.json()["error"] == "target-unknown"
    assert h.githost.pushes == []


def test_a_node_that_is_not_the_targets_is_refused_as_the_gate_would(h: Harness) -> None:
    r = post(
        h, sign_in(h, "code_owner"), body(proof={"node": "no-such", "attestation": ATTESTATION})
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "registration-proof-unknown"
    assert h.githost.pushes == []


def test_an_attestation_the_graph_lacks_is_refused(h: Harness) -> None:
    r = post(h, sign_in(h, "code_owner"), body(proof={"node": NODE, "attestation": "000999"}))
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "registration-attestation-unknown"
    assert h.githost.pushes == []


@pytest.mark.parametrize("how", ["other-node", "failed", "unreadable"])
def test_an_attestation_that_is_not_the_nodes_passing_one_is_refused(
    h: Harness, tree: Path, how: str
) -> None:
    if how == "other-node":
        attest(tree, "000040", node_id="tutorial-and-swap")
    elif how == "failed":
        attest(tree, "000040", verdict="fail", first_failing_step=4)
    else:
        (tree / "attestations" / "000040.json").write_text("not json", encoding="utf-8")
    serve_tree(h, tree)
    r = post(h, sign_in(h, "code_owner"), body(proof={"node": NODE, "attestation": "000040"}))
    assert r.status_code == 400, (how, r.text)
    assert r.json()["error"] == "registration-attestation-mismatch"
    assert h.githost.pushes == []


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"registry": "zenodo"}, "record-invalid"),
        ({"status": "pending"}, "record-invalid"),
        ({"graph_commit": "abc"}, "record-invalid"),
        ({"wrapper": {"repository": "o/r"}}, "arguments-invalid"),
        ({"wrapper": "o/r@" + SHA}, "arguments-invalid"),
        ({"proof": {"node": NODE}}, "arguments-invalid"),
        ({"proof": {"node": NODE, "attestation": 38}}, "arguments-invalid"),
        ({"url": "http://palomar-registry.org/x"}, "record-invalid"),
        ({"registry_id": "PAL-1"}, "record-invalid"),
        ({"version": 0}, "record-invalid"),
        ({"note": ""}, "record-invalid"),
        ({"note": "x" * 1001}, "field-too-long"),
    ],
)
def test_bad_arguments_are_400_and_open_nothing(
    h: Harness, over: dict[str, Any], code: str
) -> None:
    r = post(h, sign_in(h, "code_owner"), body(**over))
    assert r.status_code == 400, (over, r.text)
    assert r.json()["error"] == code, (over, r.json())
    assert h.githost.pushes == []


def test_the_submitter_is_the_sign_in_never_a_field(h: Harness) -> None:
    r = post(h, sign_in(h, "code_owner"), body(submitted_by="somebody-else"))
    assert r.status_code == 400, r.text
    assert h.githost.pushes == []


def test_the_daily_limit_is_the_stewards_limit(tree: Path) -> None:
    for h in harness_over(tree, {"OPN_API_STEWARDS_PER_DAY": "1"}):
        owner = sign_in(h, "code_owner")
        assert post(h, owner, body()).status_code == 201
        h.clock.advance(seconds=90)
        r = post(h, owner, body(version=2))
        assert r.status_code == 429 and r.json()["error"] == "rate-limited"
        assert r.headers["Retry-After"]


# --- the tools --------------------------------------------------------------------------------


def test_register_target_is_the_route_body_for_body(h: Harness, tree: Path) -> None:
    token = h.token_for("code_owner", "owner-agent")
    out = McpClient(h).ok("register_target", body(), token=token)
    assert out["status"] == 201
    assert out["body"]["path"].endswith("2026-09-09-1.yaml")
    push = h.githost.pushes[-1]
    doc = yaml.safe_load(push.files[out["body"]["path"]])
    assert doc["submitted_by"] == CURATOR and doc["schema"] == "registration/v1"


def test_register_target_passes_a_refusal_through(h: Harness) -> None:
    token = h.token_for("code_carol", "carol-agent")
    out = McpClient(h).failed("register_target", body(), token=token)
    assert out["status"] == 403 and out["body"]["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_register_target_needs_a_token(h: Harness) -> None:
    out = McpClient(h).failed("register_target", body())
    assert out["status"] == 401 and "get_token" in json.dumps(out["body"])


def rows(**over: Any) -> list[dict[str, Any]]:
    return [
        {
            "registry": "palomar",
            "registry_id": "PALOMAR-2026-10-12-000003",
            "version": 1,
            "status": "registered",
            "url": "https://palomar-registry.org/entries/PALOMAR-2026-10-12-000003",
        }
        | over
    ]


def publish_index(h: Harness, registrations: dict[str, list[dict[str, Any]]]) -> None:
    """The committed targets/index.json with a ``registrations`` list per target (v10's field)."""
    index = json.loads(h.githost.files["targets/index.json"])
    for row in index["targets"]:
        row["registrations"] = registrations.get(str(row["target_id"]), [])
    index["targets"].append(
        {
            **index["targets"][0],
            "target_id": "other",
            "registrations": registrations.get("other", []),
        }
    )
    h.githost.files["targets/index.json"] = json.dumps(index).encode()
    h.context.files.clear()


def test_list_registrations_reads_the_index_rows(h: Harness) -> None:
    publish_index(h, {TARGET: rows(), "other": rows(status="submitted", url=None)})
    out = McpClient(h).ok("list_registrations", {})
    assert out["count"] == 2 and out["target_id"] is None
    assert [r["target_id"] for r in out["registrations"]] == [TARGET, "other"]
    assert out["registrations"][0] == {"target_id": TARGET, **rows()[0]}
    one = McpClient(h).ok("list_registrations", {"target_id": "other"})
    assert one["count"] == 1 and one["target_id"] == "other"
    assert one["registrations"][0]["status"] == "submitted"


def test_list_registrations_on_an_index_before_v10_answers_none(h: Harness) -> None:
    """The fixture index predates the field: no row carries registrations, and the answer says
    so by listing none rather than failing (the service reads every version the products emit)."""
    out = McpClient(h).ok("list_registrations", {"target_id": TARGET})
    assert out["count"] == 0 and out["registrations"] == []


def test_list_registrations_refuses_an_unknown_target(h: Harness) -> None:
    out = McpClient(h).failed("list_registrations", {"target_id": "no-such"})
    assert out["error"] == "not-found" and out["source"] == "graph"


def test_get_target_passes_registrations_through(h: Harness) -> None:
    graph = json.loads(h.githost.files[f"targets/{TARGET}/graph.json"])
    graph["registrations"] = rows()
    h.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    h.context.files.clear()
    out = McpClient(h).ok("get_target", {"target_id": TARGET})
    assert out["registrations"] == rows()
    assert out["graph"]["registrations"] == rows()
    del graph["registrations"]
    h.githost.files[f"targets/{TARGET}/graph.json"] = json.dumps(graph).encode()
    h.context.files.clear()
    assert McpClient(h).ok("get_target", {"target_id": TARGET})["registrations"] == []
