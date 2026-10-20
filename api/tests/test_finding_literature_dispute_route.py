"""F23-T13, F05-T31, F09-T74 (D-25, D-32 v3.45): a steward or curator *disputes* a proposed
literature status as well as confirming it.

``POST /literature/confirm`` takes ``disputes`` beside ``record`` — the same grammar, exclusive
with it — and writes a signed ``literature/v2`` record naming the proposal it rejects with the
signer's own reading; ``POST /literature`` writes its proposals as ``literature/v2`` too. The
MCP's ``confirm_literature`` carries the parameter to the same route, and the service's derived
context bundle inlines each literature record's summary and references exactly as the gate's own
builder does (F10-Q7, from the service's side). Nothing the site's ``me.js`` posts today changes:
``node_id, record, status, references, summary`` still confirm.
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
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from mcp_client import NODE as MCP_NODE
from mcp_client import NODE_DIR as MCP_NODE_DIR
from mcp_client import TARGET as MCP_TARGET
from mcp_client import McpClient
from test_glosses_route import CURATOR, NODE, NODE_DIR, make_keys, make_tree
from test_glosses_route import serve as serve_tree
from test_literature_confirm_route import (
    PROPOSAL,
    STEWARD,
    body,
    harness_over,
    post,
    proposal_doc,
    verifies,
)
from test_literature_route import proposal, seed_stewards
from test_mcp_equivalence import derived_bundle, seed_graph
from test_web_session import sign_in

from opn_api import literature
from opn_api.mcp import bijection, writes
from opn_api.mcp.server import TOOLS
from opn_gate import schemas, steward

SCHEMA = "literature/v2"
CONFIRM = "confirm_literature"
BY_NAME = {t.name: t for t in TOOLS}


# The confirm route's fixtures, rebuilt over its plain helpers (importing a fixture by name
# makes every test parameter a redefinition to ruff).


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
    """The propositional fixture (alice a steward, the owner a curator) with bob's v1 proposal
    merged on the node, as the live graph carries them."""
    root = make_tree(tmp_path, keys)
    path = root / NODE_DIR / PROPOSAL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(proposal_doc(), sort_keys=False), encoding="utf-8")
    return root


@pytest.fixture
def h(tree: Path, approval: tuple[str, str]) -> Iterator[Harness]:
    yield from harness_over(tree, {"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})


def landed_v2(h: Harness, tree: Path, response: Any) -> dict[str, Any]:
    """The pushed file laid over the tree and loaded as ``literature/v2``."""
    assert response.status_code == 201, response.text
    push = h.githost.pushes[-1]
    path = response.json()["path"]
    assert list(push.files) == [path]
    over = tree.parent / "landed-v2"
    shutil.rmtree(over, ignore_errors=True)
    shutil.copytree(tree, over)
    (over / path).parent.mkdir(parents=True, exist_ok=True)
    (over / path).write_text(push.files[path], encoding="utf-8")
    doc = dict(schemas.load_yaml(over / path, SCHEMA))
    assert schemas.violations(doc, SCHEMA) == []
    return doc


def dispute(**over: Any) -> dict[str, Any]:
    """A dispute of bob's ``known``: the steward read the paper and finds the problem open."""
    return body(record=None, disputes=PROPOSAL, status="open") | over


# --- the dispute -----------------------------------------------------------------------------


@pytest.mark.parametrize("proposal_schema", ["literature/v1", "literature/v2"])
def test_a_steward_disputes_a_proposal(
    h: Harness, tree: Path, approval: tuple[str, str], proposal_schema: str
) -> None:
    """The signed record names the proposal in ``disputes`` with ``confirms`` null, carries the
    signer's reading, validates as literature/v2 and verifies under the approval key; the pull
    request says it is a dispute. A v1 proposal on the live graph can be disputed as a v2 one."""
    doc = proposal_doc() | {"schema": proposal_schema}
    if proposal_schema == SCHEMA:
        doc["disputes"] = None
    (tree / NODE_DIR / PROPOSAL).write_text(yaml.safe_dump(doc, sort_keys=False))
    serve_tree(h, tree)
    r = post(h, sign_in(h, "code_alice"), dispute())
    out = r.json()
    assert set(out) == {"pr_number", "pr_url", "branch", "path"}, out
    assert out["path"] == f"{NODE_DIR}/literature/20260909T120000Z-{STEWARD}.yaml"
    written = landed_v2(h, tree, r)
    assert written["schema"] == SCHEMA
    assert (written["contributor"], written["status"]) == (STEWARD, "open")
    assert (written["confirms"], written["disputes"]) == (None, PROPOSAL)
    assert written["via"] == "approval-key" and written["model_and_tooling"] is None
    assert written["references"] == body()["references"]
    verifies(written, approval[1])
    (pr,) = h.githost.pulls
    assert pr.title == f"literature: {NODE} disputed by {STEWARD}"
    assert "dispute" in pr.body and PROPOSAL in pr.body
    assert (tree / NODE_DIR / PROPOSAL).read_text() == yaml.safe_dump(doc, sort_keys=False)


def test_a_curator_disputes_too(h: Harness, tree: Path, approval: tuple[str, str]) -> None:
    r = post(h, sign_in(h, "code_owner"), dispute(status="elementary"))
    written = landed_v2(h, tree, r)
    assert (written["contributor"], written["status"], written["disputes"]) == (
        CURATOR,
        "elementary",
        PROPOSAL,
    )
    verifies(written, approval[1])


def test_a_confirmation_is_the_mirror_and_still_takes_what_the_site_posts(
    h: Harness, tree: Path, approval: tuple[str, str]
) -> None:
    """``me.js`` posts node_id, record, status, references, summary and nothing else: the record
    lands as literature/v2 with ``confirms`` set and ``disputes`` null."""
    r = post(h, sign_in(h, "code_alice"), body())
    written = landed_v2(h, tree, r)
    assert (written["confirms"], written["disputes"]) == (PROPOSAL, None)
    assert written["status"] == "known"
    verifies(written, approval[1])
    (pr,) = h.githost.pulls
    assert pr.title == f"literature: {NODE} confirmed by {STEWARD}"


def test_a_statement_of_ones_own_names_neither(h: Harness, tree: Path) -> None:
    r = post(h, sign_in(h, "code_alice"), body(record=None, disputes=None, status="open"))
    written = landed_v2(h, tree, r)
    assert (written["confirms"], written["disputes"]) == (None, None)


def test_the_submission_is_watchable_under_the_confirmation_kind(h: Harness) -> None:
    out = post(h, sign_in(h, "code_alice"), dispute()).json()
    r = h.client.get(f"/submissions/{out['pr_number']}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["kind"] == literature.KIND_CONFIRMATION


# --- refusals --------------------------------------------------------------------------------


def test_record_and_disputes_together_are_400_naming_both(h: Harness) -> None:
    r = post(h, sign_in(h, "code_alice"), body(disputes=PROPOSAL))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert "record" in r.json()["message"] and "disputes" in r.json()["message"]
    assert h.githost.pushes == []


def test_disputing_a_file_that_is_not_on_the_node_is_404(h: Harness) -> None:
    r = post(
        h,
        sign_in(h, "code_alice"),
        dispute(disputes="literature/20261001T090000Z-nobody.yaml"),
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "not-found"
    assert r.json()["details"]["path"].endswith("literature/20261001T090000Z-nobody.yaml")
    assert h.githost.pushes == []


def test_disputing_a_file_that_is_not_a_literature_record_is_400(h: Harness, tree: Path) -> None:
    stray = tree / NODE_DIR / "literature/20261001T090000Z-stray.yaml"
    stray.write_text("schema: postmortem/v1\n", encoding="utf-8")
    serve_tree(h, tree)
    r = post(
        h, sign_in(h, "code_alice"), dispute(disputes="literature/20261001T090000Z-stray.yaml")
    )
    assert r.status_code == 400 and r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == "disputes"
    assert h.githost.pushes == []


def test_disputing_a_signed_record_is_400(h: Harness, tree: Path) -> None:
    """Only an unsigned proposal can be disputed (D-25 v3.45): a signed record is a steward's or
    curator's reading, superseded by a later signed record, never rejected by name."""
    signed_path = "literature/20261001T100000Z-carol.yaml"
    doc = proposal_doc() | {
        "contributor": "carol",
        "date": "2026-10-01T10:00:00Z",
        "via": "approval-key",
        "key": "ssh-ed25519 AAAA",
        "signature": "-----BEGIN SSH SIGNATURE-----\nAAAA\n-----END SSH SIGNATURE-----\n",
    }
    (tree / NODE_DIR / signed_path).write_text(yaml.safe_dump(doc, sort_keys=False))
    serve_tree(h, tree)
    r = post(h, sign_in(h, "code_alice"), dispute(disputes=signed_path))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "arguments-invalid"
    assert r.json()["details"]["field"] == "disputes"
    assert "signed" in r.json()["message"]
    assert h.githost.pushes == []


@pytest.mark.parametrize(
    "value", ["attempts/x.yaml", "literature/../x.yaml", 7, "", "literature/x.txt"]
)
def test_a_malformed_disputes_is_400_naming_the_field(h: Harness, value: Any) -> None:
    r = post(h, sign_in(h, "code_alice"), dispute(disputes=value))
    assert r.status_code == 400, (value, r.text)
    assert r.json()["details"]["field"] == "disputes"
    assert h.githost.pushes == []


def test_a_dispute_by_neither_steward_nor_curator_is_403(h: Harness) -> None:
    r = post(h, sign_in(h, "code_carol"), dispute())
    assert r.status_code == 403 and r.json()["error"] == "not-steward-or-curator"
    assert h.githost.pushes == []


def test_a_dispute_without_the_signers_own_reading_is_400(h: Harness) -> None:
    """``status``, ``references`` and ``summary`` stay required: a dispute carries the signer's
    reading, never only a rejection."""
    for missing in ("status", "references", "summary"):
        doc = {k: v for k, v in dispute().items() if k != missing}
        r = post(h, sign_in(h, "code_alice"), doc)
        assert r.status_code == 400, (missing, r.text)
        assert r.json()["details"]["field"].startswith(missing), (missing, r.json())
    assert h.githost.pushes == []


# --- F05-T31: the proposal route writes v2 ---------------------------------------------------


def test_the_proposal_route_writes_literature_v2(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post("/literature", json=proposal(), headers=harness.auth(token))
    assert r.status_code == 201, r.text
    [push] = harness.githost.pushes
    doc = yaml.safe_load(next(iter(push.files.values())))
    assert doc["schema"] == SCHEMA
    assert schemas.violations(doc, SCHEMA) == []
    assert doc["confirms"] is None and doc["disputes"] is None and doc["signature"] is None
    assert literature.SCHEMA == SCHEMA


# --- F09-T74 / the MCP: confirm_literature disputes through the same route -------------------


def test_confirm_literature_declares_disputes_and_says_so() -> None:
    tool = BY_NAME[CONFIRM]
    prop = tool.input_schema["properties"]["disputes"]
    assert prop["type"] == ["string", "null"]
    assert prop["pattern"] == tool.input_schema["properties"]["record"]["pattern"]
    assert str(prop.get("description", "")).strip()
    assert "disputes" not in tool.input_schema["required"]  # me.js's five still confirm
    assert "dispute" in tool.description and "literature/v2" in tool.description
    assert "literature/v2" in BY_NAME["propose_literature"].description
    assert bijection.BY_TOOL[CONFIRM].routes == ("POST /literature/confirm",)
    assert "disputes" not in writes.RENAMES.get(CONFIRM, {})  # sent under its own name


def test_confirm_literature_with_disputes_reaches_the_route(approval: tuple[str, str]) -> None:
    """Through the bijection: one plain route, the body carrying ``disputes``, the route's own
    receipt and refusal shapes."""
    hh = make_harness({"OPN_API_APPROVAL_SIGNING_KEY": approval[0]})
    with hh.client:
        seed_stewards(hh, ("alice", steward.COMMIT))
        rejected = "literature/20261001T090000Z-bob.yaml"
        hh.githost.files[f"targets/propositional/nodes/{TUTORIAL_NODE}/{rejected}"] = (
            yaml.safe_dump(proposal_doc() | {"node": TUTORIAL_NODE}, sort_keys=False).encode()
        )
        hh.context.files.clear()
        token = hh.token_for("code_alice", "alice-agent")
        args = {
            "node_id": TUTORIAL_NODE,
            "record": None,
            "disputes": rejected,
            "status": "open",
            "references": [{"title": "Erdős problems #1", "url": None, "note": None}],
            "summary": "The cited paper proves a weaker statement; the problem is open.",
        }
        out = McpClient(hh).ok(CONFIRM, args, token=token)
        assert out["status"] == 201, out
        [push] = hh.githost.pushes
        doc = yaml.safe_load(next(iter(push.files.values())))
        assert schemas.violations(doc, SCHEMA) == []
        assert (doc["confirms"], doc["disputes"], doc["status"]) == (None, rejected, "open")
        assert doc["contributor"] == "alice"
        both = McpClient(hh).failed(CONFIRM, args | {"record": rejected}, token=token)
        assert both["status"] == 400 and "disputes" in both["body"]["message"]
        assert len(hh.githost.pushes) == 1


# --- the derived bundle inlines the record (F10-Q7, the service's side) ----------------------


def test_the_derived_context_inlines_a_proposals_summary_and_references(
    harness: Harness, tmp_path: Path
) -> None:
    """A node whose ``literature_proposed`` names a record on the host: the service's bundle,
    built through its host reader, carries the record's summary and references and equals the
    gate's own ``DiskReader`` build of the same tree (F10-Q7)."""
    seed_graph(harness)
    record = "literature/20261008T090000Z-bob.yaml"
    proposal_file = {
        "schema": "literature/v1",
        "node": MCP_NODE,
        "contributor": "bob",
        "date": "2026-10-08T09:00:00Z",
        "status": "known",
        "references": [
            {"title": "A published proof", "url": "https://example.org/paper", "note": "Thm 2."},
            {"title": "A survey", "url": None, "note": None},
        ],
        "summary": "Proved in the literature; never formalised.",
        "model_and_tooling": None,
        "confirms": None,
        "via": None,
        "key": None,
        "signature": None,
    }
    files = harness.githost.files
    files[MCP_NODE_DIR + record] = yaml.safe_dump(proposal_file, sort_keys=False).encode()
    graph = json.loads(files[f"targets/{MCP_TARGET}/graph.json"])
    for node in graph["nodes"]:
        if node["node_id"] == MCP_NODE:
            node["literature_proposed"] = {
                "status": "known",
                "record": record,
                "contributor": "bob",
            }
    files[f"targets/{MCP_TARGET}/graph.json"] = json.dumps(graph).encode()
    harness.context.files.clear()
    harness.context.listings.clear()
    served = McpClient(harness).ok("get_node", {"node_id": MCP_NODE, "include": []})
    assert served["context_source"] == "derived"
    assert served["context"]["schema"] == "context/v9"
    proposed = served["context"]["literature_proposed"]
    assert proposed["summary"] == proposal_file["summary"]
    assert proposed["references"] == proposal_file["references"]
    assert proposed["record"] == record and proposed["contributor"] == "bob"
    assert served["context"]["literature"] is None
    derived = derived_bundle(harness, tmp_path / "tree")
    assert {**derived, "claims": served["context"]["claims"]} == served["context"]
