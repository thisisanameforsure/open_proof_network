"""F12-T8 with the real toolchain (lean tier): the gate's re-run of a typed QA record.

The fast tier proves the comparison and every branch through the fake seam; this proves the
re-run is real Lean end to end — ``qa.screen`` over a head copy on the pinned toolchain, the
comparison against a record typed by hand, and a checkout left untouched. The propositional
fixture's root is a tautology, so the statement screen *proves it*: a record typing
``screen-statement: pass`` is refused naming that row, and the compile, the negation and the
False screen, which the real toolchain does not prove, agree. Core Lean only; no Mathlib.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import GRAPH, TARGET, copy_graph

from opn_gate import config, qa, qa_rerun
from opn_gate.toolchain import LocalToolchain

pytestmark = pytest.mark.lean

WHEN = "2026-09-13T12:00:00Z"


def test_the_rerun_refutes_a_typed_pass_on_a_tautology(
    tmp_path: Path, real_toolchain: LocalToolchain, lean_pkg: Path
) -> None:
    real_toolchain.lean_pkg_bin = lean_pkg
    root = copy_graph(tmp_path, GRAPH)
    target = root / "targets" / TARGET
    rows = [
        qa.row(check, "pass", tool="hand", tool_version="hand", timestamp=WHEN)
        for check in ("compile", *qa.SCREENS)
    ]
    path = qa.write(target, "root", rows, date=WHEN, produced_by="hand")
    rel = path.relative_to(root).as_posix()
    before = {p: p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}

    def rerun(target_id: str, subject: str) -> list[qa.Row]:
        copy = qa_rerun.head_copy(root, tmp_path / "head")
        ctx = qa_rerun.context(copy, target_id, real_toolchain, tmp_path / "work", config.load({}))
        return qa_rerun.rerun_subject(
            ctx, subject, date=WHEN, attempt_budget_s=120.0, subject_budget_s=600.0
        )

    report = qa_rerun.verify(root, [rel], rerun)
    by_check = {c.check: c for c in report.checked}
    assert set(by_check) == {"compile", *qa.SCREENS}
    assert by_check["screen-statement"].rerun == ("fail",), by_check["screen-statement"]
    for check in ("compile", "screen-negation", "screen-false", "screen-consequence"):
        assert by_check[check].agrees, by_check[check]
    assert [(d.code, d.details["check"]) for d in report.problems] == [
        (qa_rerun.CODE_DISAGREES, "screen-statement")
    ]
    after = {p: p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}
    assert after == before, "the re-run wrote into the tree it was checking"
