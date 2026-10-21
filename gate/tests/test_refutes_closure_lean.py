"""F28-T10 (decisions v3.46; D-12, D-30): the composed refutation against the real toolchain.

The root is ``∀ n : Nat, n < 3``; the variant ``∃ n, 3 ≤ n`` is proved; its ``Relation.lean``
(``-- relation: refutes``) proves ``variant → ¬ root``. ``close.link_text`` with the refuted
verdict writes ``theorem all_small_refuted : ¬ (∀ n : Nat, n < 3) := (relation variant)`` under
the statement's own header, and Lean 4.33.1 accepts it with no ``sorry`` — the same bench as
``test_close_compose.test_a_link_proof_elaborates``. The direction is the kernel's to guard: the
same relation composed as a *proof* of the root (the proving text) does not elaborate, so a
refutes link can never write a proving record by mistake.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from test_close_compose import Bench, bench  # noqa: F401 — the module-scoped bench, a fixture

from opn_gate import close, closure, layout

pytestmark = pytest.mark.lean

ROOT = (
    "/-- Every natural number is small. -/\ntheorem all_small : ∀ n : Nat, n < 3 := by\n  sorry\n"
)
RELATION = (
    "-- relation: refutes\n\n"
    "theorem relation : (∃ n : Nat, 3 ≤ n) → ¬ ∀ n : Nat, n < 3 :=\n"
    "  fun ⟨n, h⟩ hall => absurd (hall n) (Nat.not_lt.mpr h)\n"
)
VARIANT = "theorem big : ∃ n : Nat, 3 ≤ n := ⟨3, Nat.le_refl 3⟩\n\n"


def run_lean(b: Bench, path: Path) -> subprocess.CompletedProcess[str]:
    sysroot = b.pinned.libdir.parent.parent
    return subprocess.run(
        [str(b.tc.elan), "run", b.pinned.name, "lean", str(path)],
        cwd=b.root,
        env={
            "LEAN_PATH": str(b.pinned.libdir),
            "ELAN_HOME": str(b.tc.elan.parent.parent),
            "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
            "HOME": str(b.root),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def composed(verdict: str) -> str:
    st = layout.parse_statement(ROOT)
    assert isinstance(st, layout.Statement)
    helper = close.as_helper(RELATION, "variant", st.prefix)
    return VARIANT + close.link_text(st, helper, "big", None, verdict=verdict)


def test_the_composed_refutation_elaborates(
    bench: Bench,  # noqa: F811 — the imported fixture
) -> None:
    text = composed(closure.VERDICT_REFUTED)
    assert "theorem all_small_refuted : ¬ (∀ n : Nat, n < 3) := (opn_closing_link @_root_.big)" in (
        text
    )
    path = bench.root / "Refutes.lean"
    path.write_text(text, encoding="utf-8")
    proc = run_lean(bench, path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "sorry" not in proc.stdout + proc.stderr


def test_the_kernel_refuses_the_same_relation_as_a_proof_of_the_root(
    bench: Bench,  # noqa: F811 — the imported fixture
) -> None:
    path = bench.root / "RefutesAsProof.lean"
    path.write_text(composed(closure.VERDICT_PROVED), encoding="utf-8")
    proc = run_lean(bench, path)
    assert proc.returncode != 0
    assert "type mismatch" in proc.stdout + proc.stderr
