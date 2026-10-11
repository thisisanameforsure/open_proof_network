"""F02-T11, lean tier: an ``initialize`` block in the artifact cannot supply a judging verdict.

Step 2 accepts a ``Proof.lean`` with a command after its body (F08-Q36; the owner's ruling is to
add no rule about what one may contain), so an artifact can declare ``initialize`` code. Until
T11 two judging programs ran it: ``opn-statement-meaning`` imported the artifact with
initializers enabled, and step 5's probe was ``lean`` on a file importing it (the frontend
enables them). Code there can print a verdict-shaped line and exit 0 before the program speaks:
the meaning parser took the last line and the axioms parser the first that named the
declaration. Now neither program executes anything of the artifact's, and each verdict is the
one line tagged with the caller's nonce.

Both cases need the real toolchain and the built Lake package; they run in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_uses_defs_lean import context, submit

from opn_gate import layout, pipeline
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean


def lean_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def initializer(*lines: str) -> str:
    """An ``initialize`` block that prints ``lines`` and exits 0, as forged output would."""
    prints = "".join(f"  IO.println {lean_string(line)}\n" for line in lines)
    return f"\n\ninitialize do\n{prints}  IO.Process.exit 0\n"


def test_an_initializer_cannot_answer_the_meaning_comparison(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The T23 instance trap (a false statement that reads true under ``import Defs.Trap``),
    with an ``initialize`` that prints the comparison's "matches" and exits. Refused at step 4,
    as without it. Before T11 the forged line was the verdict and the run went on to step 5."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-zero", real_toolchain)
    forged = {
        "ok": True,
        "decl": "OpnProp.size_is_zero",
        "expected": "x",
        "declared": "x",
        "identical": True,
        "matches": True,
        "locals": [],
        "local_mismatch": [],
    }
    submit(ctx, "Defs.Trap", " by\n  intro n\n  rfl" + initializer(json.dumps(forged)))
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic


def test_an_initializer_cannot_answer_the_axioms_query(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """A true statement "proved" with ``sorry``, and an ``initialize`` that prints both shapes of
    a clean axioms answer (``#print axioms``'s and ``opn-axioms``'s) and exits. Step 5 reads the
    proof term, finds ``sorryAx`` and refuses it."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-id", real_toolchain)
    decl = "OpnProp.size_is_id"
    module = layout.node_module("size-is-id", "Proof")
    clean = json.dumps({"ok": True, "decl": decl, "module": module, "axioms": []})
    submit(
        ctx,
        "Defs.Twice",
        " by\n  intro n\n  have _h : Opn.twice 1 = 2 := rfl\n  sorry"
        + initializer(f"'{decl}' does not depend on any axioms", clean),
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 5
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "axiom-not-allowed", verdict.diagnostic
    assert "sorryAx" in verdict.diagnostic.details["axioms"]
