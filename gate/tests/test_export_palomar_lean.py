"""F25-T8 / AC9 (F25-R11): the exported wrapper of the propositional fixture, checked at the
graph's pin with the real toolchain — every module elaborates under the module-system headers,
the kernel replays the Solution afresh, its axioms are the allowed ones, and
``opn-statement-meaning`` says the Solution's theorem has the Challenge's type.

Also F25-Q2's answer at the pin for a core-only project: Lean 4.33.1 accepts ``module``,
``public import`` and ``@[expose] public section``. The Mathlib half (oleans built without the
module system) is the docker tier's question, ``test_export_palomar_docker.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_export_palomar import ready, run

from opn_gate import palomar_check
from opn_gate import palomar_export as ex
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean


def test_the_fixture_export_checks_out_at_the_pin(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    root = ready(tmp_path)
    exported = run(root)
    project = tmp_path / "wrapper"
    exported.write(project)
    report = palomar_check.local_check(
        real_toolchain,
        pinned,
        project,
        package=exported.package,
        decl=exported.decl,
        allowlist=["propext", "Classical.choice", "Quot.sound"],
        timeout_s=600,
    )
    names = {c.name: c for c in report.checks}
    assert all(c.ok for c in report.checks), [c for c in report.checks if not c.ok]
    assert report.ok
    assert set(report.modules) == {
        f"{exported.package}.Nodes.and_reassoc",
        f"{exported.package}.Nodes.tutorial_and_swap",
        exported.package,
        "Solution",
        "Challenge",
    }
    assert names["statement-meaning"].ok and names["replay Solution (fresh)"].ok
    allowed = {"propext", "Classical.choice", "Quot.sound"}
    assert set(report.axioms) <= allowed
    written = json.loads((project / palomar_check.REPORT).read_text(encoding="utf-8"))
    assert written["ok"] is True and written["schema"] == "opn-local-check/v1"


def test_a_tampered_solution_fails_the_meaning_check(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The check is not a formality: a Solution proving a different proposition under the same
    name is refused by the kernel's comparison, as Comparator would refuse it."""
    root = ready(tmp_path)
    exported = run(root)
    project = tmp_path / "wrapper"
    exported.write(project)
    solution = project / "Solution.lean"
    text = solution.read_text(encoding="utf-8")
    weaker = (
        text.split(ex.SECTION + "\n\n", 1)[0]
        + ex.SECTION
        + "\n\n"
        + (
            "theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → True := by\n"
            "  intro p q r h\n  trivial\n"
        )
    )
    solution.write_text(weaker, encoding="utf-8")
    report = palomar_check.local_check(
        real_toolchain,
        pinned,
        project,
        package=exported.package,
        decl=exported.decl,
        allowlist=["propext", "Classical.choice", "Quot.sound"],
        timeout_s=600,
    )
    assert not report.ok
    failed = {c.name for c in report.checks if not c.ok}
    assert "statement-meaning" in failed or "record-hashes" in failed
    assert "record-hashes" in failed  # the export's hash of Solution.lean no longer matches
