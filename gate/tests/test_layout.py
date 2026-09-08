"""F00-T4: D-3 layout validation (R1; AC1, AC2)."""

from __future__ import annotations

import shutil
from pathlib import Path

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.layout import Node

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "graphs"
GRAPH = FIXTURES / "propositional"
NODES = layout.graph_nodes_dir(GRAPH, "propositional")
NODE_IDS = ("and-reassoc", "and-swap-reassoc", "tutorial-and-swap")


def test_fixture_nodes_valid() -> None:
    """AC1."""
    assert sorted(p.name for p in NODES.iterdir()) == list(NODE_IDS)
    for node_id in NODE_IDS:
        assert layout.validate_node(NODES / node_id) == []
        node = layout.load_node(NODES / node_id, "propositional")
        assert isinstance(node, Node), node
        assert node.node_id == node_id
        assert node.statement.statement_hash == node.meta["statement-hash"]


def test_missing_and_extra_entries_named(tmp_path: Path) -> None:
    """AC2."""
    missing = tmp_path / "tutorial-and-swap"
    shutil.copytree(NODES / "tutorial-and-swap", missing)
    (missing / "Witness.lean").unlink()
    found = layout.validate_node(missing)
    assert [d.code for d in found] == ["layout-missing"]
    assert "Witness.lean" in found[0].message

    stray = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", stray)
    (stray / "notes.txt").write_text("hi")
    (stray / "lakefile.lean").write_text("")
    found = layout.validate_node(stray)
    assert [d.code for d in found] == ["layout-extra", "layout-extra"]
    assert {d.message for d in found} == {
        "unexpected entry lakefile.lean",
        "unexpected entry notes.txt",
    }


def test_misnamed_entries(tmp_path: Path) -> None:
    n = tmp_path / "n"
    shutil.copytree(NODES / "and-reassoc", n)
    shutil.rmtree(n / "attempts")
    (n / "attempts").write_text("not a dir")
    found = layout.validate_node(n)
    assert [d.code for d in found] == ["layout-misnamed"]


def test_load_node_reports_meta_and_hash_problems(tmp_path: Path) -> None:
    n = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", n)
    original = (n / "Statement.lean").read_text()
    (n / "Statement.lean").write_text(original + "-- edited\n")
    result = layout.load_node(n, "propositional")
    assert isinstance(result, list)
    assert [d.code for d in result] == ["statement-hash"]
    assert set(result[0].details) == {"meta", "computed"}

    wrong_id = tmp_path / "renamed"
    shutil.copytree(NODES / "and-reassoc", wrong_id)
    result = layout.load_node(wrong_id, "propositional")
    assert isinstance(result, list)
    assert any(d.code == "meta-id" for d in result)

    bad_meta = tmp_path / "bad"
    shutil.copytree(NODES / "and-reassoc", bad_meta)
    (bad_meta / "META.yaml").write_text("schema: meta/v7\nid: bad\n")
    result = layout.load_node(bad_meta, "propositional")
    assert isinstance(result, list)
    assert result[0].code == "meta-invalid"
    assert "unknown schema" in result[0].message


def test_undeclared_dep_named(tmp_path: Path) -> None:
    nodes = tmp_path / "nodes"
    shutil.copytree(NODES / "and-swap-reassoc", nodes / "and-swap-reassoc")
    result = layout.load_node(nodes / "and-swap-reassoc", "propositional")
    assert isinstance(result, list)
    assert {d.message for d in result} == {
        "declared dep 'tutorial-and-swap' is not a node",
        "declared dep 'and-reassoc' is not a node",
    }


def test_parse_statement_shapes() -> None:
    ok = layout.parse_statement("theorem Foo.bar : True := by\n  sorry\n")
    assert not isinstance(ok, Diagnostic)
    assert ok.decl_name == "Foo.bar"
    assert ok.prefix == "theorem Foo.bar : True :="
    assert ok.suffix == "\n"

    ns = layout.parse_statement(
        "namespace A\nnamespace B\ntheorem t : True := sorry\nend B\nend A\n"
    )
    assert not isinstance(ns, Diagnostic)
    assert ns.decl_name == "A.B.t"
    assert ns.suffix == "\nend B\nend A\n"

    two = layout.parse_statement("theorem a : True := sorry\ntheorem b : True := sorry\n")
    assert isinstance(two, Diagnostic) and two.code == "statement-shape"
    none = layout.parse_statement("def x := 1\n")
    assert isinstance(none, Diagnostic)
    nobody = layout.parse_statement("theorem a : True := trivial\n")
    assert isinstance(nobody, Diagnostic)


def test_import_rule(tmp_path: Path) -> None:
    """F01-Q2: node files import only library modules, Defs.*, or their own Context."""
    assert layout.node_module("and-swap-reassoc", "Proof") == "Nodes.«and-swap-reassoc».Proof"
    assert layout.module_origin("Nodes.«tutorial-and-swap».Proof") == ("node", "tutorial-and-swap")
    assert layout.module_origin("Nodes.tutorial.Proof") == ("node", "tutorial")
    assert layout.module_origin("Mathlib.Data.Nat.Basic") == ("library", None)
    assert layout.module_origin("Defs.Graph") == ("defs", None)
    assert layout.module_origin("Context") == ("other", None)

    n = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", n)
    (n / "Statement.lean").write_text(
        "import Nodes.«tutorial-and-swap».Proof\nimport Context\n"
        + (n / "Statement.lean").read_text()
    )
    (n / "Context.lean").write_text("import Nodes.«and-reassoc».Context\n")
    found = layout.validate_node(n)
    assert [d.details["module"] for d in found] == [
        "Nodes.«tutorial-and-swap».Proof",
        "Context",
        "Nodes.«and-reassoc».Context",
    ]
    assert all(d.code == "import-forbidden" for d in found)
