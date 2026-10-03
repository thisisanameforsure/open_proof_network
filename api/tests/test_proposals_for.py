"""F18-T6: a crux proposed for a node (F18-R8, AC9; D-14 v3.26).

``POST /proposals/speculative`` and the MCP ``propose_speculative_node`` tool take an optional
``for``: the node of the same target the crux is proposed for. The service checks it against the
committed products the way the gate will — a node of the target, not the crux itself, not
superseded — and writes the ``proposed-for/`` record into the proposal pull request, authored by
the proposer's pseudonym, with the proposal's date. A bad ``for`` is refused 400 with the gate's
code before anything is pushed or opened. Driven through the route (and the MCP tool), and the
pushed tree is judged by the gate's own classifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness
from mcp_client import McpClient

from opn_api import proposals
from opn_api.mcp import writes
from opn_gate import modes, paths, proposed_for, scaffold, schemas
from opn_gate.paths import Change

TARGET = "propositional"
NODES = f"targets/{TARGET}/nodes/"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
STATEMENT = "theorem OpnProp.and_weaken : ∀ p q : Prop, p ∧ q → p ∨ q := by\n  sorry\n"  # noqa: RUF001
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
FOR = "and-reassoc"  # a ready node of the fixture graph
OLD = "listed-only"  # superseded by FOR where a test needs a superseded node


def post(h: Harness, body: dict[str, Any]) -> Any:
    token = h.token_for("code_alice", "alice")
    return h.client.post("/proposals/speculative", json=body, headers=h.auth(token))


def base(**over: Any) -> dict[str, Any]:
    return {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, **over}


def supersede(h: Harness, old: str = OLD, new: str = FOR) -> None:
    """``old`` superseded by ``new`` in the committed products, and its status record on main."""
    doc = json.loads(h.githost.files[GRAPH_PATH])
    for node in doc["nodes"]:
        if node["node_id"] == old:
            node["status"] = "superseded"
    h.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    h.context.files.pop(GRAPH_PATH, None)
    h.githost.files[f"{NODES}{old}/status/20261001T000000Z-curator.yaml"] = yaml.safe_dump(
        {
            "schema": "node-status/v1",
            "status": "superseded",
            "cause": f"revised as {new}",
            "author": "thisisanameforsure",
            "date": "2026-10-01",
            "reference": new,
        }
    ).encode()


def materialise(files: dict[str, str], root: Path) -> Path:
    for path, content in files.items():
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return root


def test_a_good_for_lands_as_the_record(harness: Harness, tmp_path: Path) -> None:
    r = post(harness, base(**{"for": FOR}))
    assert r.status_code == 201, r.text
    node_id = r.json()["node_id"]
    files = dict(harness.githost.pushes[-1].files)
    prefix = f"{NODES}{node_id}/"
    records = sorted(p for p in files if p.startswith(f"{prefix}{proposed_for.DIR}/"))
    assert len(records) == 1, sorted(files)
    (path,) = records
    # <timestamp>-<pseudonym>.yaml, the same stamp as the proposal's own status record
    (status,) = (p for p in files if p.startswith(f"{prefix}status/"))
    assert path.rsplit("/", 1)[1] == status.rsplit("/", 1)[1]
    assert path.rsplit("/", 1)[1].endswith("-alice.yaml")
    doc = yaml.safe_load(files[path])
    meta = yaml.safe_load(files[f"{prefix}META.yaml"])
    assert doc == {
        "schema": proposed_for.SCHEMA,
        "for": FOR,
        "author": "alice",
        "date": meta["provenance"]["date"],
        "note": None,
    }
    assert schemas.violations(doc) == []
    located = paths.locate(path)
    assert located is not None and located.role == "proposed-for"

    # What the service pushed is a proposal the gate accepts, record and all, on the graph it
    # will merge into: the fixture graph's nodes, plus the pushed directory.
    root = materialise(files, tmp_path / "graph")
    (root / NODES / FOR).mkdir(parents=True, exist_ok=True)
    classification = modes.classify([Change("A", p) for p in files], author="bot")
    assert classification.mode == "proposal"
    assert modes.check(root, classification) == []


def test_no_for_writes_no_record(harness: Harness) -> None:
    r = post(harness, base())
    assert r.status_code == 201, r.text
    files = harness.githost.pushes[-1].files
    assert not any(f"/{proposed_for.DIR}/" in p for p in files)


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("ghost", "proposed-for-unknown-node"),
        ("Not An Id", "proposed-for-malformed"),
        (7, "proposed-for-malformed"),
        ("", "proposed-for-malformed"),
    ],
)
def test_a_bad_for_is_refused_before_anything_is_pushed(
    harness: Harness, value: Any, code: str
) -> None:
    r = post(harness, base(**{"for": value}))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == code, r.text
    assert harness.githost.pushes == []
    assert harness.githost.pulls == []


def test_the_crux_itself_is_refused(harness: Harness) -> None:
    """The crux's id is new, so it is "self" only when it equals an existing id — the same
    statement proposed for itself."""
    node_id = scaffold.speculative_id(STATEMENT, proposals.SPECULATIVE_PREFIX)
    r = post(harness, base(**{"for": node_id}))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "proposed-for-self"
    assert harness.githost.pushes == []


def test_a_superseded_node_is_refused_naming_its_successor(harness: Harness) -> None:
    supersede(harness)
    r = post(harness, base(**{"for": OLD}))
    assert r.status_code == 400, r.text
    doc = r.json()
    assert doc["error"] == "proposed-for-superseded"
    assert doc["details"]["successor"] == FOR
    assert FOR in doc["message"]
    assert harness.githost.pushes == []


def test_the_mcp_tool_passes_it_through(harness: Harness) -> None:
    [tool] = [t for t in writes.TOOLS if t.name == "propose_speculative_node"]
    assert "for" in tool.input_schema["properties"]
    assert "proposed-for" in tool.description or "proposed for" in tool.description
    client = McpClient(harness)
    token = harness.token_for("code_alice", "alice")
    doc = client.ok(
        "propose_speculative_node",
        {"target_id": TARGET, "stmt": STATEMENT, "witness": WITNESS, "for": FOR},
        token=token,
    )
    assert doc["status"] == 201, doc
    files = harness.githost.pushes[-1].files
    (path,) = (p for p in files if f"/{proposed_for.DIR}/" in p)
    assert yaml.safe_load(files[path])["for"] == FOR

    refused = client.failed(
        "propose_speculative_node",
        {"target_id": TARGET, "stmt": STATEMENT + "\n", "witness": WITNESS, "for": "ghost"},
        token=token,
    )
    assert "proposed-for-unknown-node" in json.dumps(refused), refused
    assert len(harness.githost.pushes) == 1
