"""F11-T4 / F07-R6 dispatched: ``postmerge --apply-partial`` turns a merged partial into its hole
children, in the checkout the bot commit carries (D-12 #5, D-29, D-31).

F07-T4 built ``apply_partial`` as a pure function with no caller (F07-Q17). The on-ramp graph is
seeded by a skeleton, so the caller lands here: after the merge commit re-derives as a passing
partial, the children are written beside the parent — each statement under the parent's imports,
so a hole over a ``Defs.*`` object elaborates — the parent's deps and Context regenerated, and the
assembly filed under ``attempts/`` for the pseudonym the submission block names. Over the
scripted docker and the fake seam, like the other sandboxed-command tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fakes import FakeToolchain, artifact_result, witness_result
from test_cli_sandboxed import NODES, Seam, git_repo, run

from opn_gate import cli, schemas, submission
from opn_gate.paths import Change

ROOT = "and-swap-reassoc"
TARGET = "propositional"
STAMP_FILE = "20260912T100000Z-someone-partial.lean"
BODY = """  intro p q r h
  have right : r := sorry
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""
HOLES = [
    ("right", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", False),
    ("left", "∀ (p q r : Prop), (p ∧ q) ∧ r → r → q ∧ p", False),
]
WITNESS = witness_result(expected="∃ p q r, (p ∧ q) ∧ r", witness="∃ p q r, (p ∧ q) ∧ r")


def merged_partial(
    tmp_path: Path, *, annex: bool = False, extra_imports: str = ""
) -> tuple[Path, str, str]:
    """A repo whose HEAD merges one assembly onto the unproved root (no Proof.lean); returns
    the root dir, the assembly text and the annex hash cited (or ""). ``extra_imports`` is
    prepended to the root's statement first, in the base commit, since a statement is immutable
    once merged (D-3) and a submission's diff never modifies one."""
    root, git, _base = git_repo(tmp_path)
    node = root / NODES / ROOT
    # The fixture's root carries a proof; a partial is for a node without one, and deleting a
    # Proof.lean is never part of a submission's diff (F00-R2) — so it goes in a commit of its own.
    (node / "Proof.lean").unlink(missing_ok=True)
    if extra_imports:
        path = node / "Statement.lean"
        path.write_text(extra_imports + path.read_text(encoding="utf-8"), encoding="utf-8")
        meta = node / "META.yaml"
        doc = yaml.safe_load(meta.read_text())
        doc["statement-hash"] = schemas.content_hash(path.read_bytes())
        meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "the root, unproved")
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    digest = ""
    citation = ""
    if annex:
        prose = (
            "---\nschema: annex/v1\nnode: and-swap-reassoc\ncontributor: someone\n"
            "licence: CC-BY-4.0\n---\nSwap, then reassociate.\n"
        )
        digest = schemas.content_hash(prose.encode("utf-8"))
        (node / "annex").mkdir(exist_ok=True)
        (node / "annex" / f"{digest}.md").write_text(prose, encoding="utf-8")
        citation = f"  -- annex: {digest}\n"
    assembly = head + ":= by\n" + citation + BODY
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / STAMP_FILE).write_text(assembly, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "partial: and-swap-reassoc")
    return root, assembly, digest


def partial_seam(seam: Seam) -> None:
    seam.fake = FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=HOLES))


def argv(root: Path, out: Path, *rest: str) -> list[str]:
    return [
        "postmerge", "--graph", str(root), "--commit", "HEAD", "--pr", "9", "--target", TARGET,
        "--node", ROOT, "--review-kind", "pr-approval", "--reviewer", "rev", "--out", str(out),
        *rest,
    ]  # fmt: skip


def test_a_merged_partial_becomes_children_in_the_checkout(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, assembly, _ = merged_partial(tmp_path)
    partial_seam(seam)
    body = tmp_path / "body.md"
    body.write_text(
        "Submitted through the service.\n\n"
        + submission.render_block(
            {
                "schema": "submission-meta/v1",
                "submission_id": "01JXYZABCDEFGHJKMNPQRSTVWX",
                "identity": {"pseudonym": "some-prover", "proof_kind": "github"},
                "artifact_type": "partial",
                "tooling": {"model": None, "version": None, "harness": None},
                "precheck_job_id": "01JXYZABCDEFGHJKMNPQRSTVWY",
            }
        )
    )
    code, out, err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--pr-body-file", str(body))
    )
    assert code == cli.EXIT_PASS, err
    assert out["partial"]["children"] == [f"{ROOT}--h1", f"{ROOT}--h2"]
    assert out["partial"]["origin"] == "compiler-derived" and out["partial"]["annex"] is None
    nodes = root / NODES
    for child, (name, closed, _) in zip(out["partial"]["children"], HOLES, strict=True):
        statement = (nodes / child / "Statement.lean").read_text(encoding="utf-8")
        assert closed in statement and name in statement
        meta = yaml.safe_load((nodes / child / "META.yaml").read_text())
        assert meta["id"] == child and meta["origin"] == "compiler-derived"
        assert "sorry" in (nodes / child / "Witness.lean").read_text()  # a slot, not a witness
    parent = yaml.safe_load((nodes / ROOT / "META.yaml").read_text())
    assert parent["deps"][-2:] == [f"{ROOT}--h1", f"{ROOT}--h2"]
    context = (nodes / ROOT / "Context.lean").read_text(encoding="utf-8")
    assert f"`{ROOT}--h1`" in context and HOLES[0][1] in context
    # The assembly is filed for the pseudonym the block names, stamped with the merge's time.
    attempt = nodes / ROOT / out["partial"]["attempt"].removeprefix("")
    filed = sorted((nodes / ROOT / "attempts").glob("*-some-prover-partial.lean"))
    assert len(filed) == 1 and filed[0].read_text(encoding="utf-8") == assembly
    assert attempt.name == filed[0].name or out["partial"]["attempt"].endswith(filed[0].name)


def test_children_carry_the_parents_imports(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-Q16, F01-Q2: the child statement is stated under the parent statement's library and
    Defs imports — a hole over a Defs object elaborates — and never under the parent's own
    Context."""
    root, _assembly, _ = merged_partial(
        tmp_path,
        extra_imports="import Defs.Divides\nimport Mathlib.Tactic\n"
        "import Nodes.«and-swap-reassoc».Context\n\n",
    )
    partial_seam(seam)
    code, out, err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", "login")
    )
    assert code == cli.EXIT_PASS, (err, out.get("first_failing_step"), out.get("diagnostic"))
    child = (root / NODES / f"{ROOT}--h1" / "Statement.lean").read_text(encoding="utf-8")
    assert child.startswith("import Defs.Divides\nimport Mathlib.Tactic\n\n")
    assert "Context" not in child.split("/-!")[0]
    # With no block in the body, the login the workflow passed names the attempt.
    assert list((root / NODES / ROOT / "attempts").glob("*-login-partial.lean"))


def test_a_cited_annex_makes_skeleton_holes(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, digest = merged_partial(tmp_path, annex=True)
    partial_seam(seam)
    code, out, _err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", "curator")
    )
    assert code == cli.EXIT_PASS
    assert out["partial"]["origin"] == "skeleton-hole" and out["partial"]["annex"] == digest
    meta = yaml.safe_load((root / NODES / f"{ROOT}--h1" / "META.yaml").read_text())
    assert meta["origin"] == "skeleton-hole" and meta["schema"] == "meta/v3"


def test_without_the_flag_nothing_is_written(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The flag is what the graph's workflow passes in partial mode; an older pin is never handed
    it and writes nothing, as before (F08-Q8)."""
    root, _assembly, _ = merged_partial(tmp_path)
    partial_seam(seam)
    code, out, _err = run(capsys, *argv(root, tmp_path / "o"))
    assert code == cli.EXIT_PASS and "partial" not in out
    assert not (root / NODES / f"{ROOT}--h1").exists()


def test_the_flag_on_a_proof_merge_writes_nothing_and_says_so(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _git, _base = git_repo(tmp_path)
    code, out, err = run(
        capsys,
        "postmerge", "--graph", str(root), "--commit", "HEAD", "--pr", "7", "--target", TARGET,
        "--node", "tutorial-and-swap", "--review-kind", "tutorial", "--out", str(tmp_path / "o"),
        "--apply-partial", "--author", "x",
    )  # fmt: skip
    assert code == cli.EXIT_PASS and "partial" not in out
    assert "was not a partial" in err


def test_a_partial_with_nobody_to_credit_is_a_usage_error(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, _ = merged_partial(tmp_path)
    partial_seam(seam)
    code, _out, err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial"))
    assert code == cli.EXIT_ERROR and "--pr-body-file" in err
    assert not (root / NODES / f"{ROOT}--h1").exists()


def test_a_failing_partial_creates_no_children(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, _ = merged_partial(tmp_path)
    seam.fake = FakeToolchain(
        witness=WITNESS, artifact=artifact_result(holes=[], body_is_hole=True)
    )
    code, out, _err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", "x"))
    assert code == cli.EXIT_FAIL and out["first_failing_step"] == 4
    assert not (root / NODES / f"{ROOT}--h1").exists()
    assert not list((root / NODES / ROOT / "attempts").glob("*-x-partial.lean"))


def test_the_diff_of_the_merge_is_what_step2_reads(tmp_path: Path, seam: Seam) -> None:
    """The merge commit's diff carries the one added assembly, which is how step 2 knows the
    submission is a partial on a reproduce or a post-merge run (no --no-diff there)."""
    root, _assembly, _ = merged_partial(tmp_path)
    changes = cli.commit_changes(root, "HEAD")
    assert [c for c in changes if c.path.endswith(".lean")] == [
        Change("A", f"{NODES}/{ROOT}/attempts/{STAMP_FILE}")
    ]
    json.dumps([c.path for c in changes])  # serialisable, as the workflow's tee expects
