"""F00-T2: one trivial theorem through the real seam (make verify-lean)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

TRIVIAL = (
    "theorem OpnSmoke.trivial_and : ∀ p q : Prop, p ∧ q → q ∧ p :=\n  fun _ _ h => ⟨h.2, h.1⟩\n"
)


def test_resolve_reports_pinned_commit(pinned: ResolvedToolchain) -> None:
    assert pinned.name == "leanprover/lean4:v4.33.1"
    assert pinned.version == "4.33.1"
    assert len(pinned.githash) == 40
    assert pinned.libdir.is_dir()


def test_trivial_theorem_through_the_seam(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    src = tmp_path / "Proof.lean"
    src.write_text(TRIVIAL, encoding="utf-8")
    out = tmp_path / "out"

    elab = real_toolchain.elaborate(pinned, src, "Proof", out, timeout_s=120)
    assert elab.ok, elab
    assert elab.errors == ()

    replay = real_toolchain.kernel_replay(pinned, "Proof", [out], timeout_s=300)
    assert replay.ok, replay.output

    ax = real_toolchain.axioms(pinned, "Proof", "OpnSmoke.trivial_and", [out], tmp_path / "ax")
    assert ax.ok, ax.output
    assert ax.axioms == frozenset()


def test_elaboration_error_is_structured(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    src = tmp_path / "Proof.lean"
    src.write_text("theorem bad : True := (1 : Nat)\n", encoding="utf-8")
    elab = real_toolchain.elaborate(pinned, src, "Proof", tmp_path / "out", timeout_s=120)
    assert not elab.ok
    assert elab.errors and elab.errors[0].line == 1
