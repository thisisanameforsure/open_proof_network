"""F08-T4: revision requests and defect claims (R6, R7; AC10).

A claim bounces in the service with the D-16 rule named, and the gate repeats the same check on
what lands — so the test drives the endpoint, then materialises the pushed file into a copy of
the gate's fixture graph and runs the classifier's checks over it, and the exhibit through the
exhibit elaboration with the fake toolchain.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml
from api_fakes import TUTORIAL_NODE, Harness
from fakes import FakeToolchain

from opn_api import requests as requestsmod
from opn_gate import config, exhibits, modes, paths, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ElabResult

TARGET = "propositional"
NODE_DIR = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/"
STATEMENT_PATH = NODE_DIR + "Statement.lean"
FIXTURE_GRAPH = Path(__file__).resolve().parents[2] / "gate" / "tests" / "fixtures" / "graphs"
STATEMENT = (FIXTURE_GRAPH / "propositional" / STATEMENT_PATH).read_text()
EXHIBIT = "import Nodes.«tutorial-and-swap».Context\n\nexample : True := trivial\n"


def post(h: Harness, route: str, token: str, body: dict[str, Any]) -> Any:
    return h.client.post(route, json=body, headers=h.auth(token))


def only_file(h: Harness) -> tuple[str, str]:
    push = h.githost.pushes[-1]
    assert len(push.files) == 1
    return next(iter(push.files.items()))


def commit_statement(h: Harness) -> None:
    """The committed Statement.lean the service reads line counts from."""
    h.githost.files[STATEMENT_PATH] = STATEMENT.encode()


def gate_checks(tmp_path: Path, path: str, content: str, *, elab_ok: bool = True) -> list[str]:
    """What the gate says about the pushed file: classification, checks, exhibit elaboration."""
    root = tmp_path / "graph"
    if not root.exists():
        shutil.copytree(FIXTURE_GRAPH / "propositional", root)
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    classification = modes.classify([Change("A", path)])
    assert classification.mode == "append", classification
    assert classification.needs_gate is False
    codes = [d.code for d in modes.check(root, classification)]
    if codes:
        return codes
    spec_path = root / "targets" / TARGET / "gate-spec.json"
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, classification.node_id or ""),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=FakeToolchain(elab=ElabResult(ok=elab_ok)),
        settings=config.load({}),
    )
    return [d.code for d in exhibits.run(ctx, modes.exhibits(root, classification))]


# --- AC10: POST /defect-claims -------------------------------------------------------------------


def test_pretriage_bounce(harness: Harness, tmp_path: Path) -> None:
    """AC10: class `typo`, a line beyond the file, and no exhibit each bounce naming the D-16
    rule; a valid claim opens an append PR and the CI check passes on what landed."""
    token = harness.token_for("code_alice", "alice")
    commit_statement(harness)
    valid = {"stmt_ref": TUTORIAL_NODE, "class": "junk-value", "line": 3, "exhibit": EXHIBIT}

    typo = post(harness, "/defect-claims", token, {**valid, "class": "typo"})
    assert typo.status_code == 400, typo.text
    assert typo.json()["error"] == "defect-class"
    assert "D-16" in typo.json()["message"] and "junk-value" in typo.json()["message"]

    beyond = post(harness, "/defect-claims", token, {**valid, "line": 40})
    assert beyond.status_code == 400
    assert beyond.json()["error"] == "defect-line"
    assert f"{len(STATEMENT.splitlines())} lines" in beyond.json()["message"]
    assert post(harness, "/defect-claims", token, {**valid, "line": 0}).status_code == 400
    assert post(harness, "/defect-claims", token, {**valid, "line": "3"}).status_code == 400

    none = post(
        harness, "/defect-claims", token, {k: v for k, v in valid.items() if k != "exhibit"}
    )
    assert none.status_code == 400
    assert none.json()["error"] == "exhibit-missing"
    blank = post(harness, "/defect-claims", token, {**valid, "exhibit": "   "})
    assert blank.status_code == 400
    unknown = post(harness, "/defect-claims", token, {**valid, "stmt_ref": "ghost"})
    assert unknown.status_code == 404
    assert harness.githost.pushes == []

    ok = post(harness, "/defect-claims", token, valid)
    assert ok.status_code == 201, ok.text
    path, content = only_file(harness)
    assert path.startswith(NODE_DIR + "defects/") and path.endswith("-alice.yaml")
    doc = yaml.safe_load(content)
    assert doc["contributor"] == "alice"
    assert doc["stmt_ref"] == TUTORIAL_NODE
    assert doc["line"] == 3 and doc["class"] == "junk-value"
    assert doc["exhibit"] == EXHIBIT  # verbatim (F07-R14)
    assert schemas.violations(doc, "defect-claim/v1") == []
    located = paths.locate(path)
    assert located is not None and located.role == "defect-claim"
    assert ok.json()["pr_url"].endswith("/pull/1")

    # The CI check: the same pre-triage on the landed file, then the exhibit elaborates.
    assert gate_checks(tmp_path, path, content) == []
    # ... and the gate, not the service, is what stands between a bad exhibit and the graph.
    broken = content.replace(EXHIBIT.splitlines()[-1], "example : True := 7")
    assert gate_checks(tmp_path, path, broken, elab_ok=False) == ["exhibit-elaboration"]


def test_defect_claim_on_a_defs_file(harness: Harness, tmp_path: Path) -> None:
    """R7: a claim against a defs/ file lands under defs/defects/ and points at that file."""
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"targets/{TARGET}/defs/Helper.lean"] = b"def helper : Nat := 0\n"
    body = {
        "stmt_ref": f"{TARGET}/defs/Helper.lean",
        "class": "definition-mismatch",
        "line": 1,
        "exhibit": "example : True := trivial\n",
    }
    r = post(harness, "/defect-claims", token, body)
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path.startswith(f"targets/{TARGET}/defs/defects/")
    assert yaml.safe_load(content)["stmt_ref"] == "defs/Helper.lean"
    located = paths.locate(path)
    assert located is not None and located.role == "defect-claim" and located.node_id is None

    missing = post(harness, "/defect-claims", token, {**body, "stmt_ref": f"{TARGET}/defs/No.lean"})
    assert missing.status_code == 404 and missing.json()["error"] == "stmt-ref-unknown"
    odd = post(harness, "/defect-claims", token, {**body, "stmt_ref": "propositional/x"})
    assert odd.status_code == 400 and odd.json()["error"] == "stmt-ref-invalid"

    # The gate's pre-triage reads the defs file from the checkout it is given.
    root = tmp_path / "graph"
    shutil.copytree(FIXTURE_GRAPH / "propositional", root)
    (root / "targets" / TARGET / "defs" / "Helper.lean").write_text("def helper : Nat := 0\n")
    assert gate_checks(tmp_path, path, content) == []


# --- POST /revision-requests (D-8) ---------------------------------------------------------------


def test_revision_request(harness: Harness, tmp_path: Path) -> None:
    """R6: the record validates, lands under revisions/, and its exhibit is elaborated by the
    append gate — or the pull request fails naming it."""
    token = harness.token_for("code_alice", "alice")
    body = {
        "node_id": TUTORIAL_NODE,
        "defect_class": "vacuity",
        "evidence": {"text": "both conjuncts follow from p ∧ q alone", "exhibit": EXHIBIT},
    }
    r = post(harness, "/revision-requests", token, body)
    assert r.status_code == 201, r.text
    path, content = only_file(harness)
    assert path.startswith(NODE_DIR + "revisions/") and path.endswith("-alice.yaml")
    doc = yaml.safe_load(content)
    assert doc["contributor"] == "alice" and doc["node"] == TUTORIAL_NODE
    assert doc["defect_class"] == "vacuity"
    assert doc["evidence"]["exhibit"] == EXHIBIT
    assert schemas.violations(doc, "revision-request/v1") == []
    assert gate_checks(tmp_path, path, content) == []
    assert gate_checks(tmp_path, path, content, elab_ok=False) == ["exhibit-elaboration"]

    # Text alone is evidence too; the cap is the schema's and is named without the text.
    plain = post(harness, "/revision-requests", token, {**body, "evidence": "just prose"})
    assert plain.status_code == 201
    _, content = only_file(harness)
    assert "exhibit" not in yaml.safe_load(content)["evidence"]
    long = post(harness, "/revision-requests", token, {**body, "evidence": {"text": "x" * 2001}})
    assert long.status_code == 400 and long.json()["error"] == "field-too-long"
    assert "2000" in long.json()["message"] and "xxxx" not in long.json()["message"]

    for bad, code in (
        ({**body, "defect_class": "weaker-please"}, "defect-class"),  # D-8: that is a variant
        ({**body, "evidence": {"exhibit": EXHIBIT}}, "evidence-invalid"),
        ({**body, "evidence": {"text": ""}}, "evidence-invalid"),
        ({**body, "node_id": "ghost"}, "node-unknown"),
    ):
        r = post(harness, "/revision-requests", token, bad)
        assert r.status_code in (400, 404), (code, r.text)
        assert r.json()["error"] == code


def test_records_need_a_token(harness: Harness) -> None:
    for route, body in (
        (
            "/revision-requests",
            {"node_id": TUTORIAL_NODE, "defect_class": "vacuity", "evidence": "x"},
        ),
        (
            "/defect-claims",
            {"stmt_ref": TUTORIAL_NODE, "class": "vacuity", "line": 1, "exhibit": "x"},
        ),
    ):
        assert harness.client.post(route, json=body).status_code == 401
    assert harness.githost.pushes == []
    assert (
        tuple(schemas.load_schema("defect-claim/v1")["properties"]["class"]["enum"])
        == requestsmod.DEFECT_CLASSES
    )
