"""F00-T4: step 2 - permitted paths, statement hash, proof-is-statement (R2, R3, R19; AC3-9, 29)."""

from __future__ import annotations

import shutil
import subprocess
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


def test_waiver_path_only_with_native_decide() -> None:
    """F02-AC8, R8: waivers/native_decide.yaml is permitted only when the proof needs it."""
    changes = [
        Change("A", f"{N}/tutorial-and-swap/Proof.lean"),
        Change("A", f"{N}/tutorial-and-swap/waivers/native_decide.yaml"),
    ]
    found = paths.check_paths(changes, CLAIM)
    assert [str(d.details["path"]) for d in found] == [
        f"{N}/tutorial-and-swap/waivers/native_decide.yaml"
    ]
    assert "native_decide" in found[0].message
    assert paths.check_paths(changes, CLAIM, waiver_allowed=True) == []
    # Only that file, only added or modified, and never another waiver.
    deleted = [Change("D", f"{N}/tutorial-and-swap/waivers/native_decide.yaml")]
    assert len(paths.check_paths(deleted, CLAIM, waiver_allowed=True)) == 1
    other = [Change("A", f"{N}/tutorial-and-swap/waivers/sorry.yaml")]
    assert len(paths.check_paths(other, CLAIM, waiver_allowed=True)) == 1
    assert paths.mentions_native_decide("  exact by native_decide\n")
    assert not paths.mentions_native_decide("  exact ⟨h.2, h.1⟩\n")


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


def test_name_status_copies_and_type_changes_are_modifications() -> None:
    """A copy, a type change or an unmerged path is treated as a modification of the named
    path, so it can never slip past step 2 as an unclassified status."""
    parsed = paths.changes_from_name_status("C75\tsrc\tdst\nT\tlink\nU\tconflict\n")
    assert parsed == [Change("M", "dst"), Change("M", "link"), Change("M", "conflict")]
    assert offending_changes(parsed) == ["dst", "link", "conflict"]


def offending_changes(changes: list[Change]) -> list[str]:
    return [str(d.details["path"]) for d in paths.check_paths(changes, CLAIM)]


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        (f"{N}/tutorial-and-swap/attempts/sub/x.yaml", "nested directories"),
        (f"{N}/tutorial-and-swap/annex/sub/{'a' * 64}.md", "nested directories"),
        (f"{N}/tutorial-and-swap/attempts/../Statement.lean", "nested directories"),
        (f"{N}/tutorial-and-swap/../and-reassoc/Proof.lean", "not Proof.lean"),
        (f"{N}/tutorial-and-swap/./Proof.lean", "not Proof.lean"),
        (f"{N}/tutorial-and-swap-evil/Proof.lean", "outside the claimed node"),
        (f"{N}/tutorial-and-swap/Proof.lean.bak", "not Proof.lean"),
        (f"{N}/tutorial-and-swap/waivers/native_decide.yaml/x", "not Proof.lean"),
        ("", "outside the claimed node"),
    ],
)
def test_escapes_of_the_node_directory_are_rejected(path: str, reason: str) -> None:
    """R2: neither a nested directory, a `..` segment, a sibling whose id shares the claimed
    node's prefix, nor a suffix on Proof.lean is a permitted path."""
    found = paths.check_paths([Change("A", path)], CLAIM)
    assert [str(d.details["path"]) for d in found] == [path]
    assert reason in found[0].message


def test_precheck_records_are_the_one_nested_append() -> None:
    """D-34: attempts/precheck/<name>.json is an append; anything deeper is not."""
    ok = [Change("A", f"{N}/tutorial-and-swap/attempts/precheck/01m23sfd.json")]
    assert paths.check_paths(ok, CLAIM) == []
    deeper = [Change("A", f"{N}/tutorial-and-swap/attempts/precheck/deep/x.json")]
    assert paths.check_paths(deeper, CLAIM) == []  # step 2's grammar stops at one level ...
    assert paths.locate(deeper[0].path) is None  # ... and the mode grammar refuses it (F07-R3)
    rewritten = [Change("M", f"{N}/tutorial-and-swap/attempts/precheck/01m23sfd.json")]
    assert "append-only" in paths.check_paths(rewritten, CLAIM)[0].message


def test_deletion_under_append_only_is_named_as_such() -> None:
    found = paths.check_paths([Change("D", f"{N}/tutorial-and-swap/annex/{'a' * 64}.md")], CLAIM)
    assert len(found) == 1 and "deleted" in found[0].message and found[0].details["status"] == "D"


def test_changes_from_a_git_worktree_and_range(tmp_path: Path) -> None:
    """What pregate.sh diffs: tracked modifications plus untracked files, and a commit range
    with renames reported as delete-plus-add (never as a rename step 2 would have to reason
    about)."""
    repo = tmp_path / "graph"
    shutil.copytree(GRAPH, repo)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True, env=env, capture_output=True)

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    node = repo / N / "tutorial-and-swap"
    (node / "Proof.lean").write_text("changed\n")
    (node / "attempts" / "new.yaml").write_text("route: a\n")
    assert paths.changes_from_worktree(repo) == [
        Change("M", f"{N}/tutorial-and-swap/Proof.lean"),
        Change("A", f"{N}/tutorial-and-swap/attempts/new.yaml"),
    ]
    git("add", "-A")
    git("commit", "-q", "-m", "change")
    git("mv", f"{N}/tutorial-and-swap/Proof.lean", f"{N}/tutorial-and-swap/Old.lean")
    git("commit", "-q", "-m", "rename")
    assert paths.changes_from_git(repo, "HEAD~1") == [
        Change("A", f"{N}/tutorial-and-swap/Old.lean"),
        Change("D", f"{N}/tutorial-and-swap/Proof.lean"),
    ]
    with pytest.raises(subprocess.CalledProcessError):
        paths.changes_from_git(repo, "no-such-ref")


def test_proof_shorter_than_the_header_names_the_missing_line() -> None:
    node = tutorial()
    d = paths.check_proof_is_statement(node.statement, "/-! The tutorial node (D-27)")
    assert d is not None and d.code == "proof-not-statement"
    assert d.details["line"] == 1 and d.details["got"] == "/-! The tutorial node (D-27)"
    d = paths.check_proof_is_statement(node.statement, "")
    assert d is not None and d.details["line"] == 1 and d.details["got"] == ""


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
