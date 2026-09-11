"""F00-T4: D-3 layout validation (R1; AC1, AC2)."""

from __future__ import annotations

import shutil
from pathlib import Path

from opn_gate import layout, postmerge
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


def test_missing_node_directory_is_named(tmp_path: Path) -> None:
    """R1: a claim on a directory that does not exist is one diagnostic, not an exception."""
    found = layout.validate_node(tmp_path / "ghost")
    assert [d.code for d in found] == ["node-missing"]
    assert "ghost" in found[0].message
    loaded = layout.load_node(tmp_path / "ghost", "propositional")
    assert isinstance(loaded, list) and loaded[0].code == "node-missing"

    as_file = tmp_path / "file-not-dir"
    as_file.write_text("")
    assert [d.code for d in layout.validate_node(as_file)] == ["node-missing"]


def test_meta_with_a_foreign_schema_is_refused(tmp_path: Path) -> None:
    """R9: META.yaml validates against the schema it names; a document that is valid under some
    *other* published schema is still not a META and is refused as such."""
    n = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", n)
    (n / "META.yaml").write_text(
        "schema: waiver/v1\nkind: native_decide\njustification: not a meta\nauthor: x\n"
    )
    result = layout.load_node(n, "propositional")
    assert isinstance(result, list)
    assert [d.code for d in result] == ["meta-schema"]
    assert "waiver/v1" in result[0].message


def test_unparseable_meta_yaml_is_meta_invalid(tmp_path: Path) -> None:
    n = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", n)
    (n / "META.yaml").write_text("schema: meta/v1\nid: [unclosed\n")
    result = layout.load_node(n, "propositional")
    assert isinstance(result, list)
    assert [d.code for d in result] == ["meta-invalid"]
    assert "cannot read YAML" in result[0].message

    (n / "META.yaml").write_text("- just\n- a list\n")
    result = layout.load_node(n, "propositional")
    assert isinstance(result, list)
    assert result[0].code == "meta-invalid" and "must be an object" in result[0].message


def test_load_node_reports_statement_shape(tmp_path: Path) -> None:
    """R1: a Statement.lean that is not one sorry-bodied theorem stops the load, without a
    hash comparison against META (there is no statement to hash)."""
    n = tmp_path / "and-reassoc"
    shutil.copytree(NODES / "and-reassoc", n)
    (n / "Statement.lean").write_text(
        "theorem OpnProp.a : True := by\n  sorry\ntheorem OpnProp.b : True := by\n  sorry\n"
    )
    result = layout.load_node(n, "propositional")
    assert isinstance(result, list)
    assert [d.code for d in result] == ["statement-shape"]
    assert "found 2" in result[0].message


def test_parse_statement_rejects_sorry_before_theorem_and_two_bodies() -> None:
    before = layout.parse_statement("def helper : Nat := sorry\ntheorem t : True := trivial\n")
    assert isinstance(before, Diagnostic) and before.code == "statement-shape"
    assert "precedes" in before.message

    two_bodies = layout.parse_statement(
        "theorem t : True := by\n  sorry\ndef helper : Nat := sorry\n"
    )
    assert isinstance(two_bodies, Diagnostic) and "found 2" in two_bodies.message

    lemma = layout.parse_statement("lemma L.x : True := sorry\n")
    assert not isinstance(lemma, Diagnostic) and lemma.decl_name == "L.x"


def test_proof_and_witness_may_not_import_another_node(tmp_path: Path) -> None:
    """F01-Q2: the import rule holds for every node file, not only Statement.lean, so a proof
    cannot smuggle in a sibling's constants by importing it directly."""
    n = tmp_path / "tutorial-and-swap"
    shutil.copytree(NODES / "tutorial-and-swap", n)
    proof = n / "Proof.lean"
    proof.write_text("import Nodes.«and-reassoc».Proof\n" + proof.read_text())
    witness = n / "Witness.lean"
    witness.write_text(
        "import Defs.Helper\nimport Nodes.«and-reassoc».Statement\n" + witness.read_text()
    )
    found = layout.validate_node(n)
    assert [(d.details["file"], d.details["module"]) for d in found] == [
        ("Proof.lean", "Nodes.«and-reassoc».Proof"),
        ("Witness.lean", "Nodes.«and-reassoc».Statement"),
    ]
    # Its own Context is allowed everywhere except in Context.lean itself.
    original = NODES / "tutorial-and-swap"
    proof.write_text(
        "import Nodes.«tutorial-and-swap».Context\n" + (original / "Proof.lean").read_text()
    )
    witness.write_text((original / "Witness.lean").read_text())
    assert layout.validate_node(n) == []
    assert layout.module_origin("Nodes") == ("other", None)


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


def test_mentions_sorry_reads_code_not_comments_or_identifiers() -> None:
    """F08-Q18: the one text reading of 'this witness is a stub'. `sorry` counts as a token of
    the code; inside a line comment, a block comment (nested, or a `/-!` doc comment), a string
    literal, or as a piece of `sorryAx` / `unsorry` / `Foo.sorry`, it does not."""
    assert layout.mentions_sorry("theorem witness : True := by\n  sorry\n")
    assert layout.mentions_sorry("theorem witness : True := sorry\n")
    assert layout.mentions_sorry("theorem w : True := by\n  exact (sorry : True)\n")
    assert not layout.mentions_sorry("-- replace sorry here\ntheorem w : True := trivial\n")
    assert not layout.mentions_sorry("theorem w : True := trivial -- was sorry\n")
    assert not layout.mentions_sorry("/- a sorry in a block -/\ntheorem w : True := trivial\n")
    assert not layout.mentions_sorry(
        "/-! The witness slot. Replace `sorry` with an instance /- nested sorry -/ -/\n"
        "theorem witness : True := trivial\n"
    )
    assert not layout.mentions_sorry('theorem w : "sorry" = "sorry" := rfl\n')
    assert not layout.mentions_sorry("#print axioms sorryAx\ntheorem w : True := trivial\n")
    assert not layout.mentions_sorry("theorem w : True := unsorry\n")
    assert not layout.mentions_sorry("theorem w : True := Lean.sorry'\n")
    assert not layout.mentions_sorry("theorem w : True := Foo.sorry\n")
    # The slot the post-merge job writes is a stub; filled under its own header it is not.
    slot = postmerge.WITNESS_SLOT.format(expected="True")
    assert layout.mentions_sorry(slot)
    assert not layout.mentions_sorry(slot.replace("by\n  sorry", "trivial"))
    # A block comment that is never closed hides everything after it — still not a token.
    assert not layout.mentions_sorry("/- open forever sorry\ntheorem w : True := trivial\n")


def test_strip_comments_keeps_offsets_and_string_literals() -> None:
    src = 'theorem w : "-- not a comment" = "x" := by -- tail\n  /- a\n  b -/ rfl\n'
    stripped = layout.strip_comments(src)
    assert len(stripped.splitlines()) == len(src.splitlines())
    assert ":= by" in stripped and "tail" not in stripped  # the string did not eat the line
    assert "not a comment" not in stripped and stripped.count('"') == 4  # its body is blanked
    assert "a\n" not in stripped.split("by")[1] and stripped.endswith(" rfl\n")
    assert layout.strip_comments("no comments\n") == "no comments\n"
