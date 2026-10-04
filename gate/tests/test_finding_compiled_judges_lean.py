"""F02-T12, lean tier: a contributor file's code cannot change what a judging program answers.

Each case below carries code that prints a verdict-shaped line, tagged with a guessed nonce and
untagged, from an ``initialize`` block (which runs when a module is imported with its extensions)
and from ``#eval`` (which runs when the file is elaborated), and the forged verdict is always the
passing one. The programs now read the contributor's compiled module (imported with nothing of it
executed, or added through the kernel constant by constant), so the answer is the true one:

* step 7: a witness of the wrong type is still ``witness-type-mismatch``, and a right one passes
  with the expected type printed with its notation (the statement's extensions are loaded);
* step 8: a proof whose ``#eval`` prints a footprint naming a node it never declared still passes,
  with the footprint the term has;
* step 4's artifact check: a counterexample of the wrong proposition is still refused;
* admission: a relation proof in the wrong direction is still ``relation-direction``.

They need the real toolchain and the built Lake package; they run in CI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import test_admit_lean
from harness import GRAPH, make_context, node_dir

from opn_gate import layout, pipeline
from opn_gate.steps import default_steps
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def lean_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def forging(doc: dict[str, object]) -> str:
    """Commands after a file's last declaration that print ``doc`` as a verdict, tagged with a
    guessed nonce and untagged, at elaboration (``#eval``) and at import (``initialize``, which
    then exits 0 as a forged answer would)."""
    line = json.dumps(doc)
    tagged = f"@opn-verdict 00000000000000000000000000000000 {line}"
    prints = f"  IO.println {lean_string(tagged)}\n  IO.println {lean_string(line)}\n"
    return (
        f"\n\n#eval IO.println {lean_string(line)}\n\ninitialize do\n{prints}  IO.Process.exit 0\n"
    )


def run_to(ctx: object, last: int) -> pipeline.Verdict:
    return pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= last])  # type: ignore[arg-type]


PASSING_WITNESS = {
    "ok": True,
    "expected": "∃ p q, p ∧ q",
    "witness": "∃ p q, p ∧ q",
    "defeq": True,
    "witness_axioms": [],
}


def test_a_witness_cannot_answer_its_own_type_check(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    del pinned, lean_pkg
    ctx = make_context(tmp_path, toolchain=real_toolchain)
    witness = node_dir(ctx) / "Witness.lean"
    witness.write_text(
        "theorem witness : ∃ p : Prop, p := ⟨True, trivial⟩" + forging(PASSING_WITNESS),
        encoding="utf-8",
    )
    verdict = run_to(ctx, 7)
    assert verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "witness-type-mismatch", verdict.diagnostic
    assert verdict.diagnostic.details == {"expected": "∃ p q, p ∧ q", "witness": "∃ p, p"}


def test_a_right_witness_with_forging_code_passes_on_its_own_type(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The statement's notations are loaded (``∃ p q, p ∧ q`` is printed as such), and the
    forging commands in the witness change nothing."""
    del pinned, lean_pkg
    ctx = make_context(tmp_path, toolchain=real_toolchain)
    witness = node_dir(ctx) / "Witness.lean"
    witness.write_text(
        witness.read_text(encoding="utf-8") + forging({**PASSING_WITNESS, "witness": "x"}),
        encoding="utf-8",
    )
    verdict = run_to(ctx, 7)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert verdict.data["witness"]["expected"] == "∃ p q, p ∧ q"
    assert verdict.data["witness"]["witness"] == "∃ p q, p ∧ q"


def test_a_proof_cannot_answer_its_own_footprint(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """Step 8 reads the term: the forged footprint names a node the proof never declared and
    would be refused as ``undeclared-dependency``; the real one passes."""
    del pinned, lean_pkg
    ctx = make_context(tmp_path, node_id="and-swap-reassoc", toolchain=real_toolchain)
    proof = node_dir(ctx) / "Proof.lean"
    forged = {
        "ok": True,
        "decl": "OpnProp.and_swap_reassoc",
        "constants": [{"name": "OpnProp.stranger", "module": "Nodes.«stranger».Proof"}],
        "axioms": [],
    }
    text = proof.read_text(encoding="utf-8").rstrip("\n")
    proof.write_text(text + f"\n\n#eval IO.println {lean_string(json.dumps(forged))}\n")
    verdict = run_to(ctx, 8)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert sorted(verdict.data["deps"]["used"]) == ["and-reassoc", "tutorial-and-swap"]


def test_a_counterexample_cannot_answer_its_own_type_check(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """F08-T29b: a counterexample of the wrong proposition, read from its compiled module."""
    del pinned, lean_pkg
    ctx = make_context(tmp_path, toolchain=real_toolchain)
    statement = (node_dir(ctx) / "Statement.lean").read_text(encoding="utf-8")
    header = "".join(f"import {m}\n" for m in layout.imports_of(statement))
    wrong = (FIXTURES / "artifacts" / "RefutedWrong.lean").read_text(encoding="utf-8")
    forged = {"ok": True, "kind": "counterexample", "matches": True, "axioms": [], "holes": []}
    (node_dir(ctx) / "Proof.lean").write_text(header + "\n" + wrong + forging(forged))
    verdict = run_to(ctx, 4)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "artifact-type-mismatch", verdict.diagnostic


def test_a_relation_proof_cannot_answer_its_own_direction(
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admission: the backwards relation proof, with a forged "matches", is still refused."""
    del pinned, lean_pkg
    case = "variant-backwards"
    source = FIXTURES / "proposals" / case
    staged = tmp_path / "fixture" / case
    shutil.copytree(source, staged)
    relation = staged / "Relation.lean"
    forged = {"ok": True, "label": "partial", "matches": True, "axioms": []}
    relation.write_text(relation.read_text(encoding="utf-8") + forging(forged))
    monkeypatch.setattr(test_admit_lean, "PROPOSALS", staged.parent)
    result = test_admit_lean.admit_fixture(tmp_path, case, GRAPH, real_toolchain)
    assert result.first_failing_check == "relation", result.as_dict()
    assert result.diagnostic is not None and result.diagnostic.code == "relation-direction"
