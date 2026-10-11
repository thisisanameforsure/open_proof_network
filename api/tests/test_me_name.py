"""F25-T4 / AC15: ``POST /me/name`` and the ``set_display_name`` tool (F25-R6, R15; D-3, D-19,
D-28, D-35 v3.37).

A bearer — any identity, since the pseudonym is the identity — records the display name it
chooses to be shown by where the network names its contributors outside itself, or withdraws it
with a null name. The service writes ``names/<pseudonym>.yaml`` (``display-name/v1``) for the
bearer's own pseudonym and no other (there is no field to name another), signs it with the
network's approval key over the canonical body the gate verifies, and opens it on an ``append/``
branch the merge actor takes as it is. One writer at a time per pseudonym: while a pull request
of the bearer's still writes the file, a second is refused with nothing opened. What lands is
checked by the gate's own ``modes.check_as_service``.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_web_session import ENV, sign_in, web_headers

from opn_api import sshsig
from opn_api.store import Identity
from opn_gate import modes, names, schemas, signed
from opn_gate.signer import NAMESPACE, SshKeygenSigner

ROUTE = "/me/name"
PSEUDONYM = "alice-agent"
ORCID = "https://orcid.org/0000-0002-1825-0097"


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
def tree(tmp_path: Path, keys: dict[str, Path], approval: tuple[str, str]) -> Path:
    """The propositional fixture with the approval key published at keys/approval.pub, which is
    where the gate reads it from the merge's parent tree."""
    root = make_tree(tmp_path, keys)
    (root / "keys").mkdir(exist_ok=True)
    (root / signed.APPROVAL_KEY_PATH).write_text(approval[1] + "\n", encoding="utf-8")
    return root


def harness_over(tree: Path, env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness({**ENV, **env})
    serve_tree(h, tree)
    with h.client:
        yield h


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


@pytest.fixture
def token(h: Harness) -> str:
    return h.token_for("code_alice", PSEUDONYM)


def post(h: Harness, token: str, doc: dict[str, Any]) -> Any:
    return h.client.post(ROUTE, json=doc, headers=h.auth(token))


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
    doc = dict(schemas.load_yaml(over / path, "display-name/v1"))
    return doc, "; ".join(d.code for d in problems)


def verifies(doc: dict[str, Any], public: str) -> None:
    assert doc["key"].split()[:2] == public.split()[:2]
    assert signed.verifies(doc, SshKeygenSigner())  # ssh-keygen -Y verify, the gate's verifier
    assert sshsig.verify(signed.body(doc), doc["signature"], doc["key"], namespace=NAMESPACE)


# --- the record ----------------------------------------------------------------------------------


def test_a_bearer_sets_the_name_of_its_own_pseudonym(
    h: Harness, tree: Path, token: str, approval: tuple[str, str]
) -> None:
    r = post(h, token, {"name": "Alice Agent", "link": ORCID})
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}
    assert out["branch"].startswith("append/"), "the merge actor takes append/ as it is"
    assert out["path"] == f"names/{PSEUDONYM}.yaml"
    doc, verdict = landed(h, tree, r)
    assert verdict == "", "the gate admits what the service wrote"
    assert (doc["pseudonym"], doc["name"], doc["link"]) == (PSEUDONYM, "Alice Agent", ORCID)
    assert (doc["date"], doc["via"]) == ("2026-09-09", "approval-key")
    verifies(doc, approval[1])
    assert names.display_name(tree.parent / "landed", PSEUDONYM) == "Alice Agent"
    assert h.githost.pushes[-1].author is not None
    assert h.githost.pushes[-1].author.name == PSEUDONYM
    (pr,) = h.githost.pulls
    assert pr.title == f"display name: {PSEUDONYM}"
    assert "display name" in pr.body


def test_the_link_is_optional(h: Harness, tree: Path, token: str) -> None:
    doc, verdict = landed(h, tree, post(h, token, {"name": "Alice Agent"}))
    assert verdict == "" and doc["link"] is None


def test_a_null_name_withdraws_it(h: Harness, tree: Path, token: str) -> None:
    doc, verdict = landed(h, tree, post(h, token, {"name": None}))
    assert verdict == "" and doc["name"] is None and doc["link"] is None
    assert names.display_name(tree.parent / "landed", PSEUDONYM) is None


def test_a_tutorial_identity_is_a_pseudonym_too(h: Harness, tree: Path) -> None:
    """D-19: the identity is the pseudonym, however it was proved; a name needs no GitHub."""
    held = Identity("01TUTORIAL", "tutor", "tutorial", "job-1", "2026-09-09T12:00:00Z")
    h.store.put_identity(held)
    from opn_api import identity as identitymod  # noqa: PLC0415

    raw, record = identitymod.issue(h.context, held.id, h.clock.now())
    h.store.put_token(record)
    doc, verdict = landed(h, tree, post(h, raw, {"name": "The Tutor"}))
    assert verdict == "" and doc["pseudonym"] == "tutor"


def test_a_later_record_replaces_the_file(h: Harness, tree: Path, token: str) -> None:
    """One file per pseudonym: the second write modifies it, which the gate allows for this role
    alone, and the history is the trail."""
    first = post(h, token, {"name": "Alice Agent"})
    merged = tree / first.json()["path"]
    merged.parent.mkdir(exist_ok=True)
    merged.write_text(h.githost.pushes[-1].files[first.json()["path"]], encoding="utf-8")
    serve_tree(h, tree)
    h.githost.set_pull_request_state(first.json()["pr_number"], state="closed", merged=True)
    h.context.pulls.clear()  # the service re-reads the host, as it would after its cache window
    h.clock.advance(seconds=90)
    doc, verdict = landed(h, tree, post(h, token, {"name": "A. Agent"}))
    assert verdict == "" and doc["name"] == "A. Agent"


def test_the_submission_is_watchable_under_its_own_kind(h: Harness, token: str) -> None:
    out = post(h, token, {"name": "Alice Agent"}).json()
    r = h.client.get(f"/submissions/{out['pr_number']}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["kind"] == "display-name"


# --- refusals, each with nothing opened -----------------------------------------------------------


def test_one_writer_at_a_time_per_pseudonym(h: Harness, token: str) -> None:
    first = post(h, token, {"name": "Alice Agent"})
    assert first.status_code == 201
    h.clock.advance(seconds=90)
    r = post(h, token, {"name": "Alice A."})
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "display-name-in-review"
    assert r.json()["details"]["pr_number"] == first.json()["pr_number"]
    assert len(h.githost.pushes) == 1
    # Another pseudonym is not held by it.
    other = h.token_for("code_bob", "bob-agent")
    assert post(h, other, {"name": "Bob"}).status_code == 201
    # Once the first is closed, the pseudonym may write again.
    h.githost.set_pull_request_state(first.json()["pr_number"], state="closed", merged=False)
    h.context.pulls.clear()
    again = post(h, token, {"name": "Alice A."})
    assert again.status_code == 201, again.text


def test_there_is_no_field_to_name_another_pseudonym(h: Harness, token: str) -> None:
    r = post(h, token, {"name": "Alice Agent", "pseudonym": "somebody-else"})
    assert r.status_code == 400, r.text
    assert h.githost.pushes == []


def test_no_bearer_is_401_and_a_web_session_alone_is_not_a_bearer(h: Harness) -> None:
    assert h.client.post(ROUTE, json={"name": "x"}).status_code == 401
    cookie = sign_in(h, "code_alice")
    assert h.client.post(ROUTE, json={"name": "x"}, headers=web_headers(cookie)).status_code == 401
    assert h.githost.pushes == []


@pytest.mark.parametrize(
    "doc",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 201},
        {"name": 7},
        {"name": "Alice", "link": "http://example.org"},
        {"name": "Alice", "link": "https://" + "x" * 500},
        {"name": None, "link": ORCID},
    ],
)
def test_bad_arguments_are_400_naming_the_field(
    h: Harness, token: str, doc: dict[str, Any]
) -> None:
    r = post(h, token, doc)
    assert r.status_code == 400, (doc, r.text)
    assert r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] in ("name", "link")
    assert h.githost.pushes == []


def test_without_the_approval_key_the_route_is_503(tree: Path) -> None:
    for h in harness_over(tree, {}):
        token = h.token_for("code_alice", PSEUDONYM)
        r = post(h, token, {"name": "Alice Agent"})
        assert r.status_code == 503 and r.json()["error"] == "approval-key-missing"
        assert h.githost.pushes == []


def test_the_daily_limit_is_the_stewards_limit(tree: Path, approval: tuple[str, str]) -> None:
    for h in harness_over(
        tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0], "OPN_API_STEWARDS_PER_DAY": "1"}
    ):
        token = h.token_for("code_alice", PSEUDONYM)
        first = post(h, token, {"name": "Alice Agent"})
        assert first.status_code == 201
        h.githost.set_pull_request_state(first.json()["pr_number"], state="closed", merged=True)
        h.context.pulls.clear()
        h.clock.advance(seconds=90)
        r = post(h, token, {"name": "A. Agent"})
        assert r.status_code == 429 and r.json()["error"] == "rate-limited"
        assert r.headers["Retry-After"]


# --- the tool ---------------------------------------------------------------------------------


def test_set_display_name_is_the_route_body_for_body(h: Harness, token: str) -> None:
    out = McpClient(h).ok("set_display_name", {"name": "Alice Agent", "link": ORCID}, token=token)
    assert out["status"] == 201 and out["body"]["path"] == f"names/{PSEUDONYM}.yaml"
    assert len(h.githost.pushes) == 1


def test_set_display_name_withdraws_with_null(h: Harness, token: str) -> None:
    out = McpClient(h).ok("set_display_name", {"name": None}, token=token)
    assert out["status"] == 201


def test_set_display_name_passes_a_refusal_through(h: Harness, token: str) -> None:
    McpClient(h).ok("set_display_name", {"name": "Alice Agent"}, token=token)
    h.clock.advance(seconds=90)
    out = McpClient(h).failed("set_display_name", {"name": "A."}, token=token)
    assert out["status"] == 409 and out["body"]["error"] == "display-name-in-review"


def test_set_display_name_needs_a_token(h: Harness) -> None:
    out = McpClient(h).failed("set_display_name", {"name": "x"})
    assert out["status"] == 401
