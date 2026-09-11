"""F04 rejection cases: the generator refuses and writes nothing (R13, AC11; C7).

Every test here mutates one thing in an otherwise valid checkout and proves the failure is
loud, named, and leaves the output directory untouched. The model's contract is "validated at
the boundary"; these tests walk that boundary case by case.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fixture
import pytest

from opn_gate import schemas
from opn_site import cli, model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
ROOT_NODE = "and-swap-reassoc"


def _read(root: Path, rel: str) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads((root / rel).read_text(encoding="utf-8"))
    return doc


def _write(root: Path, rel: str, doc: dict[str, Any]) -> None:
    (root / rel).write_bytes(schemas.canonical_json(doc))


def _render_cli(root: Path, out: Path, commit: str = fixture.COMMIT) -> int:
    return cli.main(["render", "--graph", str(root), "--commit", commit, "--out", str(out)])


def _refused(root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
    """Run the cli, assert nothing was written, return the JSON error string."""
    out = tmp_path / "out"
    assert _render_cli(root, out) == 1
    assert not out.exists()
    captured = capsys.readouterr()
    assert captured.err.startswith("opn-site: nothing written: ")
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    return str(payload["error"])


# --- products -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel", ["info.json", "frontier.json", "targets/index.json", f"targets/{TARGET}/graph.json"]
)
def test_missing_product_is_refused(
    rel: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R13: each of the four products is required; its absence names it and points at F03."""
    root = fixture.build(tmp_path)
    (root / rel).unlink()
    error = _refused(root, tmp_path, capsys)
    assert f"product {rel} is missing" in error and "opn-gate products" in error


def test_malformed_json_product_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A product that is not JSON at all is a validation failure, not a traceback."""
    root = fixture.build(tmp_path)
    (root / "info.json").write_text("{not json", encoding="utf-8")
    error = _refused(root, tmp_path, capsys)
    assert "product info.json does not validate" in error


def test_product_with_unknown_schema_id_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A product declaring a schema this repo does not know cannot be validated: refused."""
    root = fixture.build(tmp_path)
    doc = _read(root, "frontier.json")
    doc["schema"] = "frontier/v99"
    _write(root, "frontier.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "frontier.json does not validate" in error


def test_valid_document_of_the_wrong_schema_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that validates against *a* schema but not one the generator renders for that
    product is refused with the accepted versions named (D-34: parse by version)."""
    root = fixture.build(tmp_path)
    spec = _read(root, f"targets/{TARGET}/gate-spec.json")  # a valid gate-spec/v1 document
    _write(root, "info.json", spec)
    error = _refused(root, tmp_path, capsys)
    assert "product info.json is gate-spec/v1, which this generator does not render" in error
    assert "info/v1" in error


def test_unknown_status_value_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A status outside the schema's enum never reaches the renderer's fallback wording."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"][0]["status"] = "kinda-proved"
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "graph.json does not validate" in error


@pytest.mark.parametrize("node_id", ["../../etc/passwd", "And-Reassoc", "ünd-reassoc", "a b"])
def test_node_id_outside_the_identifier_pattern_is_refused(
    node_id: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Traversal, uppercase, unicode and whitespace ids are stopped at the schema, so no such id
    ever becomes a path under nodes/ or a link on a page."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"][0]["node_id"] = node_id
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "graph.json does not validate" in error


@pytest.mark.parametrize("target_id", ["../../tmp", "Propositional"])
def test_target_id_outside_the_identifier_pattern_is_refused(
    target_id: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = fixture.build(tmp_path)
    doc = _read(root, "targets/index.json")
    doc["targets"][0]["target_id"] = target_id
    _write(root, "targets/index.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "targets/index.json does not validate" in error


# --- the checkout behind the products -------------------------------------------------------------


def test_stale_graph_json_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """graph.json claiming a statement hash the checkout does not have is stale, not rendered."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"][0]["statement_hash"] = "0" * 64
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "graph.json is stale" in error and "and-reassoc" in error


def test_graph_json_naming_a_node_absent_from_the_checkout_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dangling node reference: the row exists, the directory does not."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"][0]["node_id"] = "ghost"
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert error.startswith("node ghost:")


def test_node_missing_its_statement_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The gate's own layout rules apply: a node without Statement.lean is unrenderable."""
    root = fixture.build(tmp_path)
    (root / "targets" / TARGET / "nodes" / "and-reassoc" / "Statement.lean").unlink()
    error = _refused(root, tmp_path, capsys)
    assert error.startswith("node and-reassoc:") and "Statement.lean" in error


def test_missing_gate_spec_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = fixture.build(tmp_path)
    (root / "targets" / TARGET / "gate-spec.json").unlink()
    error = _refused(root, tmp_path, capsys)
    assert "gate-spec.json" in error


def test_root_absent_from_graph_nodes_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """graph.json's root must be one of its nodes; the Targets page renders the root's statement."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["root"] = "nowhere"
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "nowhere" in error


def test_target_with_no_nodes_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A target whose graph.json lists no nodes has no root to render."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"] = []
    _write(root, f"targets/{TARGET}/graph.json", doc)
    _refused(root, tmp_path, capsys)


def test_duplicate_node_ids_in_graph_json_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two rows with one id cannot both be rendered; the product is malformed."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    doc["nodes"].append(dict(doc["nodes"][0]))
    _write(root, f"targets/{TARGET}/graph.json", doc)
    _refused(root, tmp_path, capsys)


def test_dependency_cycle_in_graph_json_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R6: the DAG layout raises on a cycle and the cli turns that into a refusal."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    by_id["and-reassoc"]["deps"] = [ROOT_NODE]  # the root already depends on and-reassoc
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "dependency cycle" in error


def test_dangling_dep_in_graph_json_is_refused_by_the_link_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dep that is not a node would become a link to a page that does not exist (R13)."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    by_id[ROOT_NODE]["deps"].append("phantom")
    _write(root, f"targets/{TARGET}/graph.json", doc)
    error = _refused(root, tmp_path, capsys)
    assert "broken links" in error and "/nodes/propositional/phantom/" in error


def test_attestation_that_is_not_json_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = fixture.build(tmp_path)
    (root / "attestations" / "000001.json").write_text("{", encoding="utf-8")
    _refused(root, tmp_path, capsys)


def test_attestation_missing_required_fields_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An attestation that matches a proved node but lacks its steps cannot be rendered (R5)."""
    root = fixture.build(tmp_path)
    path = root / "attestations" / "000001.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["steps"]
    path.write_bytes(schemas.canonical_json(doc))
    _refused(root, tmp_path, capsys)


def test_prose_that_is_not_utf8_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Undecodable contributor text is refused rather than rendered as mojibake or dropped."""
    root = fixture.build(tmp_path)
    explainer = root / "targets" / TARGET / "nodes" / "tutorial-and-swap" / "explainer" / "why.md"
    explainer.write_bytes(b"---\nauthor: x\n---\n\xff\xfe not utf-8\n")
    _refused(root, tmp_path, capsys)


def test_invalid_ledger_file_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """R8: a ledger file that fails its schema stops the build instead of being skipped."""
    root = fixture.build(tmp_path)
    (root / "ledger").mkdir()
    (root / "ledger" / "mallory.json").write_text('{"schema": "ledger/v1"}', encoding="utf-8")
    error = _refused(root, tmp_path, capsys)
    assert "ledger/v1" in error and "'identity' is a required property" in error


def test_ledger_entry_for_a_node_that_does_not_exist_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A ledger row links to its node page; a node that was never rendered is a broken link."""
    root = fixture.build(tmp_path)
    doc = {
        "schema": "ledger/v1",
        "identity": "alice",
        "entries": [
            {
                "line": "proof",
                "target": TARGET,
                "node": "never-existed",
                "artifact": "Proof.lean",
                "merge_commit": "1" * 40,
                "date": "2026-09-10T12:00:00Z",
                "tooling": "undeclared",
                "status": "active",
            }
        ],
    }
    (root / "ledger").mkdir()
    (root / "ledger" / "alice.json").write_bytes(schemas.canonical_json(doc))
    error = _refused(root, tmp_path, capsys)
    assert "broken links" in error and "never-existed" in error


# --- the cli ------------------------------------------------------------------------------------


def test_nonexistent_graph_path_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    error = _refused(tmp_path / "no-such-checkout", tmp_path, capsys)
    assert "product info.json is missing" in error


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["render"],
        ["render", "--graph", "g", "--commit", "c"],
        ["deploy", "--graph", "g", "--commit", "c", "--out", "o"],
    ],
)
def test_incomplete_arguments_exit_with_usage_error(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """argparse's exit code 2 is distinct from the generator's 1, so a caller can tell a bad
    invocation from an unrenderable graph."""
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_refusal_writes_nothing_even_when_out_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC11 with a previous site in place: a failed render leaves the old files byte-identical."""
    root = fixture.build(tmp_path)
    out = tmp_path / "out"
    assert _render_cli(root, out) == 0
    capsys.readouterr()
    before = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    (root / "frontier.json").unlink()
    assert _render_cli(root, out) == 1
    capsys.readouterr()
    after = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    assert before == after


# --- degenerate but valid inputs -----------------------------------------------------------------


def test_empty_graph_renders_every_fixed_page(tmp_path: Path) -> None:
    """A graph with no targets is a valid site: zero counts, no rows, an explicit empty frontier."""
    root = fixture.build(tmp_path)
    index = _read(root, "targets/index.json")
    index["targets"] = []
    _write(root, "targets/index.json", index)
    frontier = _read(root, "frontier.json")
    frontier["entries"] = []
    _write(root, "frontier.json", frontier)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert {"index.html", "targets/index.html", "frontier/index.html"} <= set(files)
    assert not any(rel.startswith("nodes/") for rel in files)
    assert '<td class="n">0</td><td><a href="/targets/">targets</a>' in files["index.html"]
    assert "The frontier is empty" in files["frontier/index.html"]
    assert '<section class="target-card">' not in files["targets/index.html"]


def test_proved_node_without_proof_commit_renders_without_a_proof_link(tmp_path: Path) -> None:
    """A proved row with no proof commit is contradictory but valid; the page says no proof is
    merged rather than inventing a link (R5)."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    by_id["and-reassoc"]["proof_commit"] = None
    _write(root, f"targets/{TARGET}/graph.json", doc)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = files["nodes/propositional/and-reassoc/index.html"]
    assert "No proof merged yet." in page and "No attestation" in page
    assert "/Proof.lean" not in page


def test_attestation_for_another_commit_is_not_shown(tmp_path: Path) -> None:
    """R5: only the attestation whose merge commit matches the graph's proof commit is the
    node's; a stray one for the same statement at another commit is ignored."""
    root = fixture.build(tmp_path)
    doc = _read(root, f"targets/{TARGET}/graph.json")
    by_id = {n["node_id"]: n for n in doc["nodes"]}
    by_id["and-reassoc"]["proof_commit"] = "5" * 40
    _write(root, f"targets/{TARGET}/graph.json", doc)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = files["nodes/propositional/and-reassoc/index.html"]
    assert "No attestation" in page and "attestations/000002.json" not in page
    assert f"Proof merged in commit <code>{'5' * 12}</code>" in page


def test_rendering_is_deterministic(tmp_path: Path) -> None:
    """Two renders of one checkout are byte-identical, on disk as in memory (D-36: rebuilt on
    every merge, so a merge that changes nothing must change no page)."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    first = render.render_site(site, repo_url=REPO)
    second = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert first == second
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    render.write(first, out_a)
    render.write(second, out_b)
    rel_a = {p.relative_to(out_a): p.read_bytes() for p in out_a.rglob("*") if p.is_file()}
    rel_b = {p.relative_to(out_b): p.read_bytes() for p in out_b.rglob("*") if p.is_file()}
    assert rel_a == rel_b and set(rel_a) == {Path(rel) for rel in first}
