"""Finding B: ``opn-gate revise`` pins ``revision-request/v1`` and refuses a v2 request.

D-34 versions a schema rather than editing it, so both versions are live: the append path
accepts either (``paths.SCHEMAS_FOR_ROLE``), and F12-R11's watcher writes v2 — the only version
that carries its ``upstream-drift`` class. A curator acts on that request by versioning the root
(F08-R9; F12-Q16), so ``revise`` must take a v2 request with the same effects as a v1 one, and
refuse a version outside the accepted set by naming the set (the ``records._latest_record``
pattern).

The v2 request here is built from the watcher's own constants, so it is the shape
``watch._revision_request`` writes: contributor the watcher, class ``upstream-drift``, no exhibit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import GRAPH, TARGET, copy_graph

from opn_gate import cli, curator, layout, paths, products, records, schemas, watch

ROOT = "and-swap-reassoc"
INTERIOR = "and-reassoc"
TUTORIAL = "tutorial-and-swap"
AUTHOR = "thisisanameforsure"
DATE = "2026-09-10T12:13:14Z"
NEW_STATEMENT = (
    "import Nodes.«and-reassoc-v2».Context\n\n"
    "/-! Revised: the hypothesis the original lacked (D-8). -/\n\n"
    "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
)


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def add_dependent(root: Path, node_id: str, dep: str) -> None:
    meta_path = nodes_dir(root) / node_id / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [*meta["deps"], dep]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))


def v2_request_doc(node_id: str) -> dict[str, Any]:
    """What F12-R11's watcher writes (``watch._revision_request``)."""
    return {
        "schema": watch.REVISION_SCHEMA,
        "node": node_id,
        "contributor": watch.WATCHER,
        "defect_class": watch.UPSTREAM_DRIFT,
        "evidence": {
            "text": "upstream changed the imported path between the pin and head (D-10 v3.12)."
        },
        "date": DATE[:10],
    }


def v1_request_doc(node_id: str) -> dict[str, Any]:
    return samples.revision_request(node=node_id, contributor="alice")


def write_doc(root: Path, node_id: str, doc: dict[str, Any]) -> Path:
    path = nodes_dir(root) / node_id / "revisions" / "20260910T000000-request.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    return path


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def latest_status(root: Path, node_id: str) -> records.StatusRecord:
    record = records.load_node_status(nodes_dir(root) / node_id)
    assert record is not None, node_id
    return record


def assert_revised(root: Path, revision: curator.Revision, defect_class: str) -> None:
    """test_revise_flow's effects (AC13), for a request of either version."""
    assert revision.new_id == f"{INTERIOR}-v2"
    assert set(revision.dependents) == {ROOT, TUTORIAL}
    new_dir = nodes_dir(root) / revision.new_id
    assert layout.validate_node(new_dir) == []
    meta = yaml.safe_load((new_dir / "META.yaml").read_text())
    assert meta["supersedes"] == INTERIOR and meta["id"] == revision.new_id
    assert schemas.violations(meta) == []
    assert (new_dir / "Witness.lean").read_text() == (
        nodes_dir(root) / INTERIOR / "Witness.lean"
    ).read_text()
    assert (new_dir / "Statement.lean").read_text() == NEW_STATEMENT
    assert (nodes_dir(root) / INTERIOR / "Statement.lean").read_text() == (
        GRAPH / "targets" / TARGET / "nodes" / INTERIOR / "Statement.lean"
    ).read_text()

    superseded = latest_status(root, INTERIOR)
    assert superseded.status == "superseded"
    assert superseded.doc["reference"] == revision.new_id
    assert revision.request in superseded.doc["cause"]
    assert defect_class in superseded.doc["cause"]
    for dependent in (ROOT, TUTORIAL):
        stale = latest_status(root, dependent)
        assert stale.status == "stale" and stale.doc["reference"] == INTERIOR

    prod = products.generate(root, rendered_from=None, commit_time=DATE)
    tg = prod.targets[0]
    assert tg.statuses[INTERIOR] == "superseded"
    assert tg.statuses[revision.new_id] == "ready"
    frontier = json.loads(prod.files[Path("frontier.json")])
    assert [e["node_id"] for e in frontier["entries"]] == [revision.new_id]


# --- the premise -----------------------------------------------------------------------------


def test_the_watcher_writes_a_v2_request_the_append_path_accepts() -> None:
    """The premise of the finding: v2 is the watcher's version, it validates, and v1 cannot
    carry its class — so a v2-only request is a real, current record."""
    doc = v2_request_doc(INTERIOR)
    assert watch.REVISION_SCHEMA == "revision-request/v2"
    assert "revision-request/v2" in paths.SCHEMAS_FOR_ROLE["revision-request"]
    assert schemas.violations(doc) == []
    assert schemas.violations({**doc, "schema": "revision-request/v1"}) != []


# --- library ---------------------------------------------------------------------------------


def test_revise_acts_on_a_v2_request(tmp_path: Path) -> None:
    """Failed before F12-T7: ``revise`` validated against v1 alone and raised SchemaError
    ``$['schema']: 'revision-request/v1' was expected`` (F12-Q18)."""
    root = copy_graph(tmp_path)
    add_dependent(root, TUTORIAL, INTERIOR)
    request = write_doc(root, INTERIOR, v2_request_doc(INTERIOR))
    revision = curator.revise(
        root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE
    )
    assert_revised(root, revision, watch.UPSTREAM_DRIFT)


def test_revise_still_acts_on_a_v1_request(tmp_path: Path) -> None:
    """Passes today and must keep passing: v1 stays live (D-34)."""
    root = copy_graph(tmp_path)
    add_dependent(root, TUTORIAL, INTERIOR)
    request = write_doc(root, INTERIOR, v1_request_doc(INTERIOR))
    revision = curator.revise(
        root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE
    )
    assert_revised(root, revision, "missing-hypothesis")


def test_revise_refuses_an_unknown_version_naming_the_accepted_set(tmp_path: Path) -> None:
    """A version outside the set is refused, the refusal names every accepted version, and
    nothing is written (C7). Failed before F12-T7: the message named v1 only."""
    root = copy_graph(tmp_path)
    request = write_doc(
        root, INTERIOR, {**v1_request_doc(INTERIOR), "schema": "revision-request/v9"}
    )
    before = tree(root)
    with pytest.raises(ValueError, match="revision-request/v9") as refused:
        curator.revise(root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    assert isinstance(refused.value, (schemas.SchemaError, curator.CuratorError))
    message = str(refused.value)
    for accepted in paths.SCHEMAS_FOR_ROLE["revision-request"]:
        assert accepted in message, message
    assert tree(root) == before


# --- through the entry point -----------------------------------------------------------------


def run_revise(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], doc_for: Any
) -> tuple[Path, int, dict[str, Any], str]:
    root = copy_graph(tmp_path)
    request = write_doc(root, INTERIOR, doc_for(INTERIOR))
    statement = tmp_path / "S.lean"
    statement.write_text(NEW_STATEMENT)
    code = cli.main(
        [
            "revise",
            "--graph",
            str(root),
            "--author",
            AUTHOR,
            "--date",
            DATE,
            INTERIOR,
            "--statement",
            str(statement),
            "--request",
            str(request),
        ]
    )
    captured = capsys.readouterr()
    out: dict[str, Any] = json.loads(captured.out) if captured.out.strip() else {}
    return root, code, out, captured.err


def test_cli_revise_acts_on_a_v2_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Failed before F12-T7: the SchemaError surfaced as a curator refusal — exit 1,
    ``{"ok": false, "refused": "document does not satisfy 'revision-request/v1': ..."}``."""
    root, code, out, err = run_revise(tmp_path, capsys, v2_request_doc)
    assert code == cli.EXIT_PASS, (out, err)
    assert out["ok"] is True and out["revision"] == f"{INTERIOR}-v2"
    assert all((root / w).is_file() for w in out["written"])


def test_cli_revise_still_acts_on_a_v1_request(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _root, code, out, err = run_revise(tmp_path, capsys, v1_request_doc)
    assert code == cli.EXIT_PASS, (out, err)
    assert out["ok"] is True and out["revision"] == f"{INTERIOR}-v2"
