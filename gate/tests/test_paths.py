"""F00-T4: step 2 - permitted paths, statement hash, proof-is-statement (R2, R3, R19; AC3-9, 29)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from opn_gate import layout, paths
from opn_gate.diagnostic import Diagnostic
from opn_gate.layout import Node
from opn_gate.paths import Change, Claim

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
DIFFS = FIXTURES / "diffs"
CLAIM = Claim("propositional", "tutorial-and-swap")
N = "targets/propositional/nodes"


def diff(name: str) -> list[Change]:
    return paths.changes_from_name_status((DIFFS / f"{name}.txt").read_text())


def offending(name: str) -> list[str]:
    return [str(d.details["path"]) for d in paths.check_paths(diff(name), CLAIM)]


def test_rejects_statement_edit() -> None:
    """AC3."""
    assert offending("statement-edit") == [f"{N}/tutorial-and-swap/Statement.lean"]


def test_rejects_other_node() -> None:
    """AC4."""
    assert offending("other-node") == [f"{N}/and-reassoc/Proof.lean"]


def test_rejects_defs() -> None:
    """AC5."""
    assert offending("defs") == ["targets/propositional/defs/Helper.lean"]


def test_rejects_meta_edit() -> None:
    """AC6."""
    assert offending("meta-edit") == [f"{N}/tutorial-and-swap/META.yaml"]


def test_accepts_proof_and_attempt_append() -> None:
    """AC7."""
    assert paths.check_paths(diff("proof-and-attempt"), CLAIM) == []
    assert paths.check_paths(diff("proof-and-annex"), CLAIM) == []


def test_rejects_attempt_rewrite() -> None:
    """AC8."""
    found = paths.check_paths(diff("attempt-rewrite"), CLAIM)
    assert [str(d.details["path"]) for d in found] == [
        f"{N}/tutorial-and-swap/attempts/2026-09-01-route-x.yaml"
    ]
    assert "append-only" in found[0].message


@pytest.mark.parametrize(
    ("case", "path"),
    [
        ("proof-delete", f"{N}/tutorial-and-swap/Proof.lean"),
        ("witness-edit", f"{N}/tutorial-and-swap/Witness.lean"),
        ("explainer-with-proof", f"{N}/tutorial-and-swap/explainer/why.md"),
        ("workflow", ".github/workflows/evil.yml"),
    ],
)
def test_other_forbidden_paths(case: str, path: str) -> None:
    assert offending(case) == [path]


def test_submitted_manifest_is_a_path_offence() -> None:
    assert offending("manifest") == ["lake-manifest.json", "lean-toolchain"]


def test_rename_reports_both_paths() -> None:
    change = Change("R", f"{N}/tutorial-and-swap/Proof.lean", f"{N}/tutorial-and-swap/Old.lean")
    found = paths.check_paths([change], CLAIM)
    assert [str(d.details["path"]) for d in found] == [
        f"{N}/tutorial-and-swap/Proof.lean",
        f"{N}/tutorial-and-swap/Old.lean",
    ]


def test_name_status_parsing() -> None:
    parsed = paths.changes_from_name_status("A\ta/b\nM\tc\nR100\told\tnew\nD\tgone\n\n")
    assert parsed == [
        Change("A", "a/b"),
        Change("M", "c"),
        Change("R", "new", "old"),
        Change("D", "gone"),
    ]


def test_changes_from_trees(tmp_path: Path) -> None:
    base = tmp_path / "base"
    head = tmp_path / "head"
    shutil.copytree(GRAPH, base)
    shutil.copytree(GRAPH, head)
    node = head / N / "tutorial-and-swap"
    (node / "Proof.lean").write_text("changed")
    (node / "attempts" / "new.yaml").write_text("route: a")
    (head / N / "and-reassoc" / "Witness.lean").unlink()
    assert paths.changes_from_trees(base, head) == [
        Change("D", f"{N}/and-reassoc/Witness.lean"),
        Change("M", f"{N}/tutorial-and-swap/Proof.lean"),
        Change("A", f"{N}/tutorial-and-swap/attempts/new.yaml"),
    ]


# --- content checks ----------------------------------------------------------------------------


def tutorial() -> Node:
    node = layout.load_node(
        layout.graph_nodes_dir(GRAPH, "propositional") / "tutorial-and-swap", "propositional"
    )
    assert isinstance(node, Node)
    return node


def test_statement_hash_mismatch() -> None:
    """AC9."""
    node = tutorial()
    assert paths.check_statement_hash(node.statement, node.meta) is None
    tampered = dict(node.meta)
    tampered["statement-hash"] = "0" * 64
    d = paths.check_statement_hash(node.statement, tampered)
    assert d is not None
    assert d.code == "statement-hash"
    assert d.details == {"meta": "0" * 64, "computed": node.statement.statement_hash}


def test_proof_is_statement_with_body() -> None:
    """AC29."""
    node = tutorial()
    st = node.statement
    good = node.proof_path.read_text()
    assert paths.check_proof_is_statement(st, good) is None

    renamed = good.replace("OpnProp.and_swap", "OpnProp.and_swap2")
    d = paths.check_proof_is_statement(st, renamed)
    assert d is not None and d.code == "proof-not-statement" and d.details["line"] == 3

    weakened = good.replace("p ∧ q → q ∧ p", "p ∧ q → p ∧ q")
    d = paths.check_proof_is_statement(st, weakened)
    assert d is not None and d.details["line"] == 3

    extra_import = "import Std\n" + good
    d = paths.check_proof_is_statement(st, extra_import)
    assert d is not None and d.details["line"] == 1

    helper_before = good.replace(
        "theorem OpnProp.and_swap", "theorem helper : True := trivial\ntheorem OpnProp.and_swap"
    )
    d = paths.check_proof_is_statement(st, helper_before)
    assert d is not None and d.details["line"] == 3

    term_body = st.prefix + " fun _ _ h => ⟨h.2, h.1⟩\n"
    assert paths.check_proof_is_statement(st, term_body) is None

    empty = st.prefix + "\n"
    d = paths.check_proof_is_statement(st, empty)
    assert d is not None and d.code == "proof-empty"


def test_proof_respects_trailing_namespace_end() -> None:
    parsed = layout.parse_statement("namespace A\ntheorem t : True := by\n  sorry\nend A\n")
    assert not isinstance(parsed, Diagnostic)
    assert (
        paths.check_proof_is_statement(
            parsed, "namespace A\ntheorem t : True := by\n  trivial\nend A\n"
        )
        is None
    )
    d = paths.check_proof_is_statement(parsed, "namespace A\ntheorem t : True := by\n  trivial\n")
    assert d is not None and "trailing" in d.message
